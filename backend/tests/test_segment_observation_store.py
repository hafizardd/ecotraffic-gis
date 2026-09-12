from datetime import datetime, timezone
import uuid

from app.services.segment_observation import SegmentTrafficObservation
from app.services.segment_observation_store import observation_row


def test_observation_row_preserves_audit_fields_and_raw_counts():
    observation = SegmentTrafficObservation(
        camera_id="camera-a",
        road_segment_id="segment-1",
        lane_or_stream_id="northbound",
        captured_at=datetime(2026, 9, 3, 10, tzinfo=timezone.utc),
        observation_duration_seconds=60,
        raw_detected_count={"car": 3},
    )
    segment_id = uuid.uuid4()
    camera_id = uuid.uuid4()
    row = observation_row(observation, road_segment_database_id=segment_id, camera_database_id=camera_id)

    assert row["road_segment_id"] == segment_id
    assert row["camera_id"] == camera_id
    assert row["camera_identifier"] == "camera-a"
    assert row["raw_detected_count"]["car"] == 3
    assert row["vehicle_count_semantics"] == "interval_count"
