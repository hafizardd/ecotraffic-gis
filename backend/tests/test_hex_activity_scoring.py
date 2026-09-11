from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.hex_activity_scoring import (
    HEX_AHP_WEIGHTS,
    hourly_hex_volumes,
    minmax_normalize,
    recompute_hour_scores,
)

HOUR = datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc)


def _hex(hex_id, norm_poi, norm_penduduk):
    return SimpleNamespace(hex_id=hex_id, norm_poi=norm_poi, norm_penduduk=norm_penduduk)


def test_minmax_maps_extremes_to_1_and_100():
    assert minmax_normalize(10, 10, 20) == 1.0
    assert minmax_normalize(20, 10, 20) == 100.0
    assert minmax_normalize(15, 10, 20) == pytest.approx(50.5)


def test_minmax_degenerate_spread_is_the_observed_maximum():
    assert minmax_normalize(7, 7, 7) == 100.0


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
                         "klasifikasi_potensi": None, "data_status": "no_data"}
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
    ])
    volumes = await hourly_hex_volumes(db, HOUR)
    assert volumes == {7: 18.0}


@pytest.mark.asyncio
async def test_hourly_hex_volumes_skips_segments_without_usable_sample():
    db = _DB([
        [_means_row("SEG-1", car=4.0), _means_row("SEG-2")],
        [("SEG-1", 2)],
    ])
    volumes = await hourly_hex_volumes(db, HOUR)
    assert volumes == {2: 4.0}


@pytest.mark.asyncio
async def test_hourly_hex_volumes_skips_segments_outside_grid():
    db = _DB([[_means_row("SEG-1", car=4.0)], []])
    assert await hourly_hex_volumes(db, HOUR) == {}
