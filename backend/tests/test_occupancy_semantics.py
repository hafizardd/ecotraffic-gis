from datetime import datetime, timezone

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics


def test_snapshot_occupancy_does_not_become_hourly_volume():
    captured_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    observation = SegmentTrafficObservation(
        camera_id="cam", road_segment_id="seg", lane_or_stream_id="default",
        captured_at=captured_at, observation_duration_seconds=60,
        raw_detected_count={"car": 4},
        vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY,
    )
    result = calculate_segment_emission(
        [observation], period_start=captured_at,
        period_end=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc), road_length_km=1,
    )
    assert result["vehicle_count_semantics"] == "snapshot_occupancy"
    assert result["volume_per_hour"] is None
    assert result["volume_status"] == "unavailable"
