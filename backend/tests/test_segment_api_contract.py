import uuid
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import activity_grid
from app.api.routes.segment_emissions import _iso
from app.core.database import get_db
from app.schemas.segment_emission import SegmentEmissionMapItem


def test_map_response_is_lightweight():
    item = SegmentEmissionMapItem(
        road_segment_id="segment-1",
        total_emission=12345.67, calculated_at="2026-09-03T10:00:00Z",
    )
    assert set(item.model_dump()) == {
        "road_segment_id", "total_emission",
        "calculated_at", "observed_at", "data_age_seconds", "freshness_status",
        "vehicle_count_semantics", "source_cameras",
    }


def test_geojson_temporal_fields_serialize_as_iso_strings_or_null():
    from datetime import datetime, timezone

    moment = datetime(2026, 9, 6, 13, 0, tzinfo=timezone.utc)
    assert _iso(moment) == "2026-09-06T13:00:00+00:00"
    assert _iso(None) is None
    assert isinstance(_iso(moment), str)


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _FakeDB:
    def __init__(self, values):
        self._values = iter(values)

    async def execute(self, statement, *args, **kwargs):
        return _FakeResult(next(self._values))


def _client(values):
    app = FastAPI()
    app.include_router(activity_grid.router)

    async def fake_db():
        yield _FakeDB(values)

    app.dependency_overrides[get_db] = fake_db
    return TestClient(app)


def _hex_cell():
    return SimpleNamespace(
        hex_id=12, luas_km2=1.0, poi_total=3, poi_breakdown={"Kuliner": 3}, penduduk=100,
        volume_mean=5.0, norm_volume=50.0, norm_poi=60.0, norm_penduduk=70.0,
        skor_total_ahp=55.0, ranking=42, klasifikasi_potensi="Sedang",
        ahp_weight_version="hex-ahp-v1", source="excel",
    )


def test_segment_activity_grid_returns_primary_hex_feature():
    segment = SimpleNamespace(id=uuid.uuid4())
    response = _client([segment, _hex_cell(), {"type": "Polygon", "coordinates": []}]).get(
        "/api/spatial/segments/SEG-0001/activity-grid"
    )
    assert response.status_code == 200
    properties = response.json()["properties"]
    assert properties["hex_id"] == 12
    assert properties["klasifikasi_potensi"] == "Sedang"
    assert properties["skor_total_ahp"] == 55.0


def test_segment_activity_grid_404_when_segment_missing():
    response = _client([None]).get("/api/spatial/segments/SEG-9999/activity-grid")
    assert response.status_code == 404


def test_segment_activity_grid_404_when_uncovered():
    response = _client([SimpleNamespace(id=uuid.uuid4()), None]).get(
        "/api/spatial/segments/SEG-0001/activity-grid"
    )
    assert response.status_code == 404
    assert "not covered" in response.json()["detail"]
