from datetime import datetime, timedelta, timezone

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


def test_measured_durations_are_normalized_per_stream():
    result = aggregate_segment_observations(
            [observation(duration=60), observation(camera="camera-b", stream="southbound", duration=30)],
            period_start=BASE,
            period_end=BASE + timedelta(minutes=1),
        )
    assert result.volume_per_hour["motorcycle"] == 180
    assert result.stream_durations_seconds == {"northbound": 60, "southbound": 30}


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
    assert result.vehicle_count_semantics == "snapshot_occupancy"
