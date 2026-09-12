"""Unit tests for the snapshot -> hourly REPLAY conversion helpers."""

from datetime import datetime, timedelta, timezone

from scripts.build_replay_dataset import (
    METRIC_FIELDS,
    SOURCE_CALCULATION_VERSION,
    SOURCE_SEMANTICS,
    _fill_value,
    _filled_series,
    _fixed_window,
    _gap_plan,
    _replay_result,
)

BASE = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)


def _metric_values(value: float) -> dict:
    return {field: value for field in METRIC_FIELDS}


def test_window_covers_24_utc_hours_available_to_the_time_slider():
    start, end = _fixed_window(datetime(2026, 9, 10, 13, 37, tzinfo=timezone.utc))
    assert end == datetime(2026, 9, 10, 14, 0, tzinfo=timezone.utc)
    assert start == end - timedelta(hours=24)
    buckets = [start + index * timedelta(hours=1) for index in range(24)]
    assert len(buckets) == 24


def test_gap_plan_backfills_start_forward_fills_end_and_linearly_fills_interior():
    plan = _gap_plan([False, True, False, False, True, False])
    assert plan[0] == ("backward_fill", None, 1)
    assert plan[1] is None
    assert plan[2] == ("linear", 1, 4)
    assert plan[3] == ("linear", 1, 4)
    assert plan[4] is None
    assert plan[5] == ("forward_fill", 4, None)


def test_fill_value_linear_midpoint_and_edge_fallbacks():
    assert _fill_value([0.0, None, 10.0], ("linear", 0, 2), 1) == 5.0
    assert _fill_value([7.0, None, None], ("forward_fill", 0, None), 2) == 7.0
    assert _fill_value([None, None, 7.0], ("backward_fill", None, 2), 0) == 7.0


def test_filled_series_interpolates_every_metric_across_the_gap():
    buckets = [BASE + timedelta(hours=index) for index in range(4)]
    means = {
        buckets[0]: _metric_values(0.0),
        buckets[3]: _metric_values(30.0),
    }
    series = _filled_series(means, buckets, _gap_plan([True, False, False, True]))
    for field in METRIC_FIELDS:
        assert series[field] == [0.0, 10.0, 20.0, 30.0]


def test_replay_result_is_versioned_and_flags_interpolation():
    bucket = BASE + timedelta(hours=3)
    observed = bucket + timedelta(minutes=59)
    values = _metric_values(1.0)
    real = _replay_result(None, bucket, values, plan=None, sample_count=5, observed_at=observed)
    assert real["calculation_version"] == 3
    assert real["source_mode"] == "REPLAY"
    assert real["data_source"] == "HISTORICAL"
    assert real["vehicle_count_semantics"] == "snapshot_occupancy"
    assert real["calculation_metadata"]["is_interpolated"] is False
    assert real["calculation_metadata"]["interpolation_method"] is None
    assert real["calculation_metadata"]["interpolated_from"] == []
    assert real["emissions"]["totals_g_h"]["CO2"] == 1000.0
    assert real["observed_at"] == observed.isoformat()

    filled = _replay_result(None, bucket, values, plan=("linear", 1, 5), sample_count=0,
                            observed_at=None, interpolated_from=["a", "b"])
    assert filled["calculation_metadata"]["is_interpolated"] is True
    assert filled["calculation_metadata"]["interpolation_method"] == "linear"
    assert filled["calculation_metadata"]["interpolated_from"] == ["a", "b"]
    assert filled["calculation_metadata"]["source_sample_count"] == 0


def test_replay_is_only_derived_from_durable_snapshot_facts():
    # The static profile is rebuilt from the reconciler's snapshot_occupancy
    # facts (version 2), never from its own REPLAY outputs.
    assert SOURCE_SEMANTICS == "snapshot_occupancy"
    assert SOURCE_CALCULATION_VERSION == 2
