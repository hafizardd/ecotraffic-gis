from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services import hex_activity_scoring
from app.services.hex_activity_scoring import (
    HEX_AHP_WEIGHTS,
    aggregate_potential,
    hourly_hex_volumes,
    label_potential,
    minmax_normalize,
    recompute_hour_scores,
)

HOUR = datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc)


def _hex(hex_id, norm_poi, norm_penduduk, volume_mean=None):
    return SimpleNamespace(hex_id=hex_id, norm_poi=norm_poi, norm_penduduk=norm_penduduk, volume_mean=volume_mean)


def test_minmax_maps_extremes_to_1_and_100():
    assert minmax_normalize(10, 10, 20) == 1.0
    assert minmax_normalize(20, 10, 20) == 100.0
    assert minmax_normalize(15, 10, 20) == pytest.approx(50.5)


def test_minmax_degenerate_spread_is_the_observed_maximum():
    assert minmax_normalize(7, 7, 7) == 100.0


def test_recompute_borrows_nearest_volume_when_hour_has_no_sample():
    hexes = [_hex(1, 0.0, 0.0, volume_mean=10.0), _hex(2, 0.0, 0.0, volume_mean=20.0), _hex(3, 0.0, 0.0, volume_mean=30.0)]
    centroids = {1: (0.0, 0.0), 2: (0.01, 0.0), 3: (1.0, 0.0)}
    result = recompute_hour_scores(hexes, {1: 10.0, 3: 30.0}, centroids)
    # Hex 2 has no sample, so it borrows the nearest observed grid (hex 1);
    # the observed-hour range (10-30) is the normalization basis.
    assert result[2]["data_status"] == "fallback"
    assert result[2]["fallback_from"] == 1
    assert result[2]["norm_volume"] == pytest.approx(1.0)
    assert result[3]["norm_volume"] == pytest.approx(100.0)


def test_recompute_no_coverage_normalizes_against_volume_mean():
    hexes = [_hex(1, 0.0, 0.0, volume_mean=10.0), _hex(2, 0.0, 0.0, volume_mean=20.0)]
    result = recompute_hour_scores(hexes, {})
    assert result[1]["data_status"] == "fallback"
    assert result[1]["norm_volume"] == pytest.approx(1.0)
    assert result[2]["norm_volume"] == pytest.approx(100.0)


def test_recompute_uses_static_poi_population_with_live_volume():
    hexes = [_hex(1, 100.0, 100.0), _hex(2, 0.0, 0.0)]
    result = recompute_hour_scores(hexes, {1: 10.0, 2: 20.0})
    assert result[2]["data_status"] == "live" and result[2]["ranking"] == 1
    assert result[1]["data_status"] == "live" and result[1]["ranking"] == 2
    expected_1 = HEX_AHP_WEIGHTS["volume"] * 1.0 + HEX_AHP_WEIGHTS["poi"] * 100 + HEX_AHP_WEIGHTS["penduduk"] * 100
    assert result[1]["skor_total_ahp"] == pytest.approx(expected_1)
    assert result[2]["klasifikasi_potensi"] == "Sedang"
    assert result[1]["klasifikasi_potensi"] == "Sangat Rendah"


def test_recompute_missing_volume_is_null_not_zero():
    result = recompute_hour_scores([_hex(1, 50.0, 50.0), _hex(2, 50.0, 50.0)], {1: 5.0})
    assert result[2] == {"norm_volume": None, "skor_total_ahp": None, "ranking": None,
                         "klasifikasi_potensi": None, "data_status": "no_data",
                         "no_data_reason": "no_mapped_segment"}
    assert result[1]["data_status"] == "live"


def test_recompute_zero_coverage_marks_every_hex_no_data():
    result = recompute_hour_scores([_hex(1, 50.0, 50.0), _hex(2, 50.0, 50.0)], {})
    assert all(value["data_status"] == "no_data" for value in result.values())
    assert all(value["norm_volume"] is None for value in result.values())


class _Mappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _Mappings(self._rows)

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _DB:
    def __init__(self, results):
        self._results = iter(results)

    async def execute(self, statement, *args, **kwargs):
        return _Result(next(self._results))


def _means_row(segment_id, car=None, motorcycle=None, bus=None, truck=None):
    return {"segment_id": segment_id, "car_veh_h": car, "motorcycle_veh_h": motorcycle,
            "bus_veh_h": bus, "truck_veh_h": truck}


@pytest.mark.asyncio
async def test_hourly_hex_volumes_sums_vehicle_types_and_maps_hexes():
    db = _DB([
        [_means_row("SEG-1", car=10.0, motorcycle=5.0), _means_row("SEG-2", car=3.0)],
        [("SEG-1", 7), ("SEG-2", 7)],  # both map to hex 7
        [],  # no interpolated REPLAY rows
    ])
    data = await hourly_hex_volumes(db, HOUR)
    assert data.volumes[7].volume == 18.0
    assert data.volumes[7].segment_ids == ("SEG-1", "SEG-2")
    assert data.volumes[7].interpolated is False
    assert data.mapped_hex_ids == frozenset({7})


@pytest.mark.asyncio
async def test_hourly_hex_volumes_flags_interpolated_hours():
    db = _DB([
        [_means_row("SEG-1", car=10.0)],
        [("SEG-1", 7)],
        ["SEG-1"],  # REPLAY hour was gap-filled
    ])
    data = await hourly_hex_volumes(db, HOUR)
    assert data.volumes[7].interpolated is True


@pytest.mark.asyncio
async def test_hourly_hex_volumes_skips_segments_without_usable_sample():
    db = _DB([
        [_means_row("SEG-1", car=4.0), _means_row("SEG-2")],
        [("SEG-1", 2), ("SEG-2", 2)],
        [],
    ])
    data = await hourly_hex_volumes(db, HOUR)
    assert data.volumes[2].volume == 4.0
    # Hex 2 is reached by a mapped segment even though SEG-2 had no volume.
    assert data.mapped_hex_ids == frozenset({2})


@pytest.mark.asyncio
async def test_hourly_hex_volumes_skips_segments_outside_grid():
    db = _DB([[_means_row("SEG-1", car=4.0)], [], []])
    assert (await hourly_hex_volumes(db, HOUR)).volumes == {}


@pytest.mark.asyncio
async def test_latest_hex_volumes_sums_newest_facts_and_flags_interpolation(monkeypatch):
    facts = {
        "SEG-LIVE": SimpleNamespace(volume_per_hour={"car": 30.0, "motorcycle": 10.0}, ahp_metadata={}),
        "SEG-REPLAY": SimpleNamespace(
            volume_per_hour={"car": 5.0, "motorcycle": None},
            ahp_metadata={"calculation_metadata": {"is_interpolated": True}},
        ),
        "SEG-EMPTY": SimpleNamespace(volume_per_hour={"car": None}, ahp_metadata={}),
    }

    async def fake_facts(_db):
        return facts

    async def fake_primary(_db, segment_ids):
        return {"SEG-LIVE": 7, "SEG-REPLAY": 7, "SEG-EMPTY": 9}

    monkeypatch.setattr(hex_activity_scoring, "latest_observed_facts", fake_facts)
    monkeypatch.setattr(hex_activity_scoring, "_primary_hex_by_segment", fake_primary)

    data = await hex_activity_scoring.latest_hex_volumes(object())
    assert data.volumes[7].volume == 45.0
    assert data.volumes[7].segment_ids == ("SEG-LIVE", "SEG-REPLAY")
    assert data.volumes[7].interpolated is True
    # A mapped-but-volumeless segment still marks its hex, so the reason is exact.
    assert data.mapped_hex_ids == frozenset({7, 9})
    assert 9 not in data.volumes


def test_label_potential_matches_frontend_scale():
    assert label_potential("Sangat Tinggi") == 5
    assert label_potential("Tinggi") == 4
    assert label_potential("Sedang") == 3
    assert label_potential("Rendah") == 2
    assert label_potential("Sangat Rendah") == 1
    assert label_potential(None) == 0


def test_aggregate_potential_is_area_weighted_and_skips_unscored():
    assert aggregate_potential([("Sangat Tinggi", 3.0), ("Sangat Rendah", 1.0)]) == 4
    assert aggregate_potential([("Sangat Tinggi", 1.0), (None, 5.0)]) == 5
    assert aggregate_potential([(None, 1.0)]) == 0
