from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import activity_grid
from app.core.database import get_db
from app.services import hex_activity_scoring

STATIC_PROPERTY_KEYS = {
    "hex_id", "luas_km2", "poi_total", "poi_breakdown", "penduduk", "volume_mean",
    "norm_volume", "norm_poi", "norm_penduduk", "skor_total_ahp", "ranking",
    "klasifikasi_potensi", "ahp_weight_version", "source",
}


def _cell(hex_id, ranking):
    return SimpleNamespace(
        hex_id=hex_id, luas_km2=1.0, poi_total=3, poi_breakdown={"Kuliner": 3}, penduduk=100,
        volume_mean=5.0, norm_volume=50.0, norm_poi=60.0, norm_penduduk=70.0,
        skor_total_ahp=55.0, ranking=ranking, klasifikasi_potensi="Sedang",
        ahp_weight_version="hex-ahp-v1", source="excel",
    )


class _Result:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def mappings(self):
        return self

    def scalar_one(self):
        return self._scalar

    def __iter__(self):
        return iter(self._rows)


class _DB:
    def __init__(self, results):
        self._results = iter(results)

    async def execute(self, statement, *args, **kwargs):
        return next(self._results)


def _client(db):
    app = FastAPI()
    app.include_router(activity_grid.router)

    async def fake_db():
        yield db

    app.dependency_overrides[get_db] = fake_db
    return TestClient(app)


def _patch_volumes(monkeypatch, value):
    async def fake(db, hour):
        return value

    # hour_scores() lives in the service; the hourly-series route calls the
    # re-exported name from its own module, so patch both references.
    monkeypatch.setattr(hex_activity_scoring, "hourly_hex_volumes", fake)
    monkeypatch.setattr(activity_grid, "hourly_hex_volumes", fake)


def _patch_profile_hour(monkeypatch, moment):
    async def fake(db, requested):
        return moment

    monkeypatch.setattr(activity_grid, "profile_hour", fake)


def _patch_available_hours(monkeypatch, moments):
    async def fake(db):
        return moments

    monkeypatch.setattr(activity_grid, "available_hours", fake)


def test_canonical_hour_maps_any_day_to_same_hour_of_day():
    anchor = datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc)
    assert hex_activity_scoring.canonical_hour(anchor, datetime(2026, 9, 5, 7, 0, tzinfo=timezone.utc)) == datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)
    assert hex_activity_scoring.canonical_hour(anchor, datetime(2026, 9, 5, 20, 0, tzinfo=timezone.utc)) == datetime(2026, 9, 9, 20, 0, tzinfo=timezone.utc)
    assert hex_activity_scoring.canonical_hour(anchor, None) == anchor


def test_live_hour_returns_recomputed_features(monkeypatch):
    _patch_volumes(monkeypatch, {1: 10.0, 2: 20.0})
    _patch_profile_hour(monkeypatch, datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc))
    db = _DB([
        _Result(rows=[(_cell(1, 1), 110.37, -7.79), (_cell(2, 2), 110.38, -7.80)]),
        _Result(rows=[(1, {"type": "Polygon", "coordinates": []}), (2, {"type": "Polygon", "coordinates": []})]),
    ])
    response = _client(db).get("/api/spatial/activity-grid?hour=2026-09-10T13:00:00Z")
    assert response.status_code == 200
    features = response.json()["features"]
    assert [feature["properties"]["data_status"] for feature in features] == ["live", "live"]
    assert features[1]["properties"]["ranking"] == 1
    assert features[1]["properties"]["norm_volume"] is not None


def test_hour_without_coverage_is_200_with_no_data_hexes(monkeypatch):
    _patch_volumes(monkeypatch, {})
    _patch_profile_hour(monkeypatch, datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc))
    db = _DB([
        _Result(rows=[(_cell(1, 1), 110.37, -7.79)]),
        _Result(rows=[(1, {"type": "Polygon", "coordinates": []})]),
    ])
    response = _client(db).get("/api/spatial/activity-grid?hour=2020-01-01T00:00:00Z")
    assert response.status_code == 200
    properties = response.json()["features"][0]["properties"]
    assert properties["data_status"] == "no_data"
    assert properties["norm_volume"] is None
    assert properties["klasifikasi_potensi"] is None


def test_static_grid_response_is_unchanged():
    db = _DB([_Result(rows=[(_cell(1, 1), {"type": "Polygon", "coordinates": []})])])
    response = _client(db).get("/api/spatial/activity-grid")
    assert response.status_code == 200
    properties = response.json()["features"][0]["properties"]
    assert set(properties) == STATIC_PROPERTY_KEYS
    assert "data_status" not in properties


def test_aggregated_lod_rolls_native_cells_into_one_h3_cell():
    # Two native cells well inside one another, plus a distant third that must
    # land in a different H3 cell.
    db = _DB([
        _Result(rows=[
            (_cell(1, 1), 110.3700, -7.7900),
            (_cell(2, 2), 110.3710, -7.7910),
            (_cell(3, 3), 110.5000, -7.9000),
        ]),
    ])
    response = _client(db).get("/api/spatial/activity-grid?lod=medium")
    assert response.status_code == 200
    body = response.json()
    assert body["lod"] == "medium"
    assert body["resolution"] == 7
    assert len(body["features"]) == 2

    merged = next(feature for feature in body["features"] if feature["properties"]["aggregated_count"] == 2)
    ring = merged["geometry"]["coordinates"][0]
    assert len(ring) == 7 and ring[0] == ring[-1]
    properties = merged["properties"]
    assert properties["hex_id"] is None
    assert properties["h3_index"] is not None
    assert properties["source"] == "aggregated"
    assert properties["luas_km2"] == 2.0
    assert properties["poi_total"] == 6
    assert properties["penduduk"] == 200
    assert properties["skor_total_ahp"] == 55.0


def test_aggregated_lod_bbox_limits_viewport_and_breaks():
    # Only the distant cell is in the viewport, so one feature and no spread.
    db = _DB([_Result(rows=[(_cell(1, 1), 110.37, -7.79), (_cell(2, 2), 110.50, -7.90)])])
    response = _client(db).get("/api/spatial/activity-grid?lod=coarse&bbox=110.45,-7.95,110.55,-7.85")
    assert response.status_code == 200
    body = response.json()
    assert len(body["features"]) == 1
    # A single scored cell has no distribution to quantile against.
    assert body["breaks"] is None


def test_hex_hourly_series_returns_one_point_per_available_hour(monkeypatch):
    _patch_volumes(monkeypatch, {1: 10.0, 2: 20.0})
    hours = [datetime(2026, 9, 10, h, 0, tzinfo=timezone.utc) for h in (11, 12)]
    _patch_available_hours(monkeypatch, hours)
    db = _DB([
        _Result(rows=[(_cell(1, 1), 110.37, -7.79), (_cell(2, 2), 110.38, -7.80)]),
    ])
    response = _client(db).get("/api/spatial/activity-grid/1/hourly")
    assert response.status_code == 200
    body = response.json()
    assert body["hex_id"] == 1
    assert [point["hour"] for point in body["series"]] == [moment.isoformat() for moment in hours]
    assert [point["data_status"] for point in body["series"]] == ["live", "live"]


def test_available_hours_returns_static_24h_profile(monkeypatch):
    anchor = datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc)

    async def fake_anchor(db):
        return anchor

    monkeypatch.setattr(hex_activity_scoring, "profile_anchor", fake_anchor)
    response = _client(_DB([])).get("/api/spatial/activity-grid/available-hours")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "daily-profile"
    assert len(body["hours"]) == 24
    assert body["latest"] == anchor.isoformat()
    assert body["earliest"] == (anchor - timedelta(hours=23)).isoformat()
