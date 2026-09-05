from datetime import datetime, timedelta, timezone

import pytest

from app.services.ahp_calculator import aggregate_emission_criterion
from app.services.segment_aggregation import SegmentAggregationError, aggregate_segment_observations
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics


BASE = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)


def observation(camera="camera-a", stream="northbound", duration=60, semantics=VehicleCountSemantics.INTERVAL_COUNT):
    return SegmentTrafficObservation(
        camera_id=camera,
        road_segment_id="segment-1",
        lane_or_stream_id=stream,
        captured_at=BASE,
        observation_duration_seconds=duration,
        raw_detected_count={"motorcycle": 1},
        vehicle_count_semantics=semantics,
    )


def test_mixed_durations_are_rejected():
    with pytest.raises(SegmentAggregationError, match="one duration"):
        aggregate_segment_observations(
            [observation(duration=60), observation(camera="camera-b", stream="southbound", duration=30)],
            period_start=BASE,
            period_end=BASE + timedelta(minutes=1),
        )


def test_snapshot_occupancy_is_averaged_before_hourly_conversion():
    result = aggregate_segment_observations(
        [
            observation(semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY),
            observation(semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY),
        ],
        period_start=BASE,
        period_end=BASE + timedelta(minutes=1),
    )
    assert result.raw_counts["motorcycle"] == 1
    assert result.vehicle_count_semantics == "interval_count"


def test_constant_pollutant_does_not_contribute_to_k1():
    totals = {pollutant: 10.0 for pollutant in ("TSP", "NOx", "SO2", "HC", "CO", "CO2", "CH4", "N2O")}
    ranges = {pollutant: (0.0, 20.0) for pollutant in totals}
    assert aggregate_emission_criterion(totals, ranges) == pytest.approx(0.5)
    ranges["CO"] = (10.0, 10.0)
    assert aggregate_emission_criterion(totals, ranges) == pytest.approx(7 / 16)
