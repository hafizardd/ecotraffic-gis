from datetime import datetime, timezone

import pytest

from app.services.segment_observation import (
    SegmentTrafficObservation,
    VehicleCountSemantics,
)


def _observation(**overrides):
    values = {
        "camera_id": "camera-a",
        "road_segment_id": "segment-1",
        "lane_or_stream_id": "northbound",
        "captured_at": datetime(2026, 9, 3, 10, tzinfo=timezone.utc),
        "observation_duration_seconds": 60,
        "raw_detected_count": {"motorcycle": 4, "gasoline_car": 2},
    }
    values.update(overrides)
    return SegmentTrafficObservation(**values)


def test_observation_normalizes_all_canonical_categories():
    observation = _observation()
    assert observation.raw_detected_count == {
        "motorcycle": 4,
        "gasoline_car": 2,
        "diesel_car": 0,
        "bus": 0,
        "truck": 0,
    }


def test_observation_preserves_source_and_count_semantics():
    observation = _observation(vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY)
    payload = observation.to_payload()
    assert payload["road_segment_id"] == "segment-1"
    assert payload["lane_or_stream_id"] == "northbound"
    assert payload["vehicle_count_semantics"] == "snapshot_occupancy"


@pytest.mark.parametrize(
    "field_value, message",
    [(0, "greater than zero"), (-1, "greater than zero"), (float("nan"), "finite")],
)
def test_invalid_duration_is_rejected(field_value, message):
    with pytest.raises(ValueError, match=message):
        _observation(observation_duration_seconds=field_value)


def test_invalid_count_and_naive_timestamp_are_rejected():
    with pytest.raises(ValueError, match="finite and non-negative"):
        _observation(raw_detected_count={"truck": -1})
    with pytest.raises(ValueError, match="timezone-aware"):
        _observation(captured_at=datetime(2026, 9, 3, 10))
