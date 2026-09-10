from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.emission_analytics import AnalyticsFilter, export_row, serialize_fact, serialize_history, vehicle_composition
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_latest_state import SegmentLatestStateStore
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.workers.segment_calculation_worker import _pick_observations, _reconciliation_start
from cv.track_emission import FlowCounter, FlowObservationWindow
from cv.proposal_emission_factors import POLLUTANTS

BASE = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)


def test_reconciliation_advances_across_long_camera_outages():
    next_observation = BASE + timedelta(days=2)
    start = _reconciliation_start(BASE, BASE, next_observation, 60)
    assert start <= next_observation < start + timedelta(seconds=120 * 60)


def track(inside=True):
    return {"id": 7, "cls": "car", "inside_roi": inside}


def test_flow_never_recounts_a_returning_id_and_prunes_expired_ids():
    counter = FlowCounter(min_frames=1, exit_frames=2)
    counter.update([track()])
    assert counter.update([track(False)])["car"] == 1
    counter.update([track()])
    assert counter.update([track(False)])["car"] == 0
    for _ in range(counter.retention_frames):
        counter.update([])
    assert not counter._tracks


def test_flow_window_measures_duration_and_preserves_tracks_across_windows():
    window = FlowObservationWindow(10, max_gap_seconds=6)
    assert window.add({}, BASE) is None
    assert window.add({"car": 2}, BASE + timedelta(seconds=5)) is None
    counts, duration, observed_at = window.add({"car": 3}, BASE + timedelta(seconds=10.5))
    assert counts["car"] == 5
    assert duration == 10.5
    assert observed_at == BASE + timedelta(seconds=10.5)
    assert window.counts["car"] == 0


def test_capture_gaps_are_not_recorded_as_zero_flow():
    window = FlowObservationWindow(10)
    window.add({}, BASE)
    window.add({"car": 5}, BASE + timedelta(seconds=3))
    assert window.add({}, BASE + timedelta(seconds=60)) is None
    assert window.counts["car"] == 0
    window.add({}, BASE + timedelta(seconds=65))
    assert window.add({}, BASE + timedelta(seconds=70))[0]["car"] == 0


def test_multiple_intervals_and_durations_do_not_sum_hourly_rates():
    observations = [
        SegmentTrafficObservation("a", "seg", "main", BASE, 10, {"car": 2}),
        SegmentTrafficObservation("a", "seg", "main", BASE + timedelta(seconds=20), 20, {"car": 4}),
    ]
    result = calculate_segment_emission(observations, period_start=BASE, period_end=BASE + timedelta(seconds=60), road_length_km=.5)
    assert result["raw_counts"]["car"] == 6
    assert result["volume_per_hour"]["car"] == 720
    assert result["vkt_km_h"]["car"] == 360
    assert result["emissions"]["totals_g_h"]["CO"] == 14400
    assert result["calculation_mode"] == "flow_based_segment"
    assert result["calculation_version"] == 2
    assert set(result["emissions"]["totals_g_h"]) == set(POLLUTANTS)


def test_already_hourly_samples_are_averaged():
    observations = [SegmentTrafficObservation("a", "seg", "main", BASE + timedelta(seconds=i), 60,
        {"car": value}, VehicleCountSemantics.VEHICLES_PER_HOUR) for i, value in [(0, 100), (1, 200)]]
    result = calculate_segment_emission(observations, period_start=BASE, period_end=BASE + timedelta(seconds=60), road_length_km=1)
    assert result["volume_per_hour"]["car"] == 150


def test_flow_is_preferred_over_many_occupancy_records():
    def record(semantics):
        return SimpleNamespace(camera_identifier="cam", lane_or_stream_id="main", captured_at=BASE,
            observation_duration_seconds=60, raw_detected_count={"car": 2}, vehicle_count_semantics=semantics)
    chosen, note = _pick_observations([record("snapshot_occupancy")] * 100 + [record("interval_count")], "seg")
    assert len(chosen) == 1
    assert chosen[0].vehicle_count_semantics == VehicleCountSemantics.INTERVAL_COUNT
    assert note


@pytest.mark.parametrize("hours,bucket", [(1, "1m"), (3, "5m"), (12, "15m"), (24, "1h")])
def test_dynamic_bucket(hours, bucket):
    assert AnalyticsFilter(BASE, BASE + timedelta(hours=hours)).bucket()[0] == bucket


def test_filter_rejects_reversed_and_naive_ranges():
    with pytest.raises(ValueError):
        AnalyticsFilter(BASE, BASE)
    with pytest.raises(ValueError):
        AnalyticsFilter(BASE.replace(tzinfo=None), BASE + timedelta(hours=1))


def test_history_record_is_curated_with_server_side_totals():
    row = {
        "id": "1", "segment_id": "A", "segment_name": "Segment A", "corridor_id": "C", "corridor_name": "Corridor C",
        "period_start": BASE, "period_end": BASE + timedelta(minutes=1), "calculated_at": BASE + timedelta(minutes=1, seconds=2),
        "calculation_version": 2, "source_mode": "LIVE", "vehicle_count_semantics": "interval_count",
        "pollutant_totals_g_h": {p: 2000 for p in POLLUTANTS},
        "volume_per_hour": {"car": 60, "motorcycle": 30, "bus": 5, "truck": 5},
        "vkt_km_h": {"car": 30, "motorcycle": 15, "bus": 10, "truck": 10},
        "raw_counts": {}, "source_cameras": ["cam"], "source_streams": ["main"],
        "source_observation_count": 1, "observation_duration_seconds": 60,
        "aggregation_policy": "sum_independent_streams", "category_pollutant_breakdown_g_h": {},
        "ahp_metadata": {"observed_at": BASE.isoformat()},
    }
    record = serialize_history(row, now=BASE + timedelta(minutes=2))
    assert record["total_emissions_kg_h"] == 16  # 8 pollutants x 2000 g/h -> 2 kg/h each
    assert record["total_vehicles_per_hour"] == 100
    assert record["units"]["emissions"] == "kg/hour"
    assert record["detail"]["calculation_version"] == 2
    assert "pollutant_totals_g_h" not in record and "raw_counts" not in record


def test_vehicle_composition_is_server_side_and_null_safe():
    composition = vehicle_composition({"car": 60, "motorcycle": 30, "bus": 5, "truck": 5})
    assert [row["key"] for row in composition] == ["car", "motorcycle", "bus", "truck"]
    assert composition[0]["share"] == 0.6
    assert round(sum(row["share"] for row in composition), 6) == 1
    empty = vehicle_composition({"car": None, "motorcycle": None, "bus": None, "truck": None})
    assert all(row["share"] is None for row in empty)


def test_late_processed_old_observation_cannot_replace_newer_redis_state():
    class Redis:
        def __init__(self): self.values = {}
        def get(self, key): return self.values.get(key)
        def setex(self, key, ttl, value): self.values[key] = value
    store = SegmentLatestStateStore(Redis())
    newer = {"observed_at": (BASE + timedelta(seconds=20)).isoformat(), "processed_at": (BASE + timedelta(seconds=21)).isoformat()}
    older = {"observed_at": BASE.isoformat(), "processed_at": (BASE + timedelta(seconds=40)).isoformat()}
    store.save("seg", newer)
    assert store.save("seg", older)["observed_at"] == newer["observed_at"]
