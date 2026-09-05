from datetime import datetime, timedelta, timezone

import pytest

from app.services.segment_aggregation import SegmentAggregationError, aggregate_segment_observations
from app.services.segment_observation import SegmentTrafficObservation


BASE = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)


def observation(camera, stream, motorcycle=0, gasoline_car=0):
    return SegmentTrafficObservation(
        camera_id=camera, road_segment_id="segment-1", lane_or_stream_id=stream,
        captured_at=BASE, observation_duration_seconds=60,
        raw_detected_count={"motorcycle": motorcycle, "gasoline_car": gasoline_car},
    )


def test_independent_streams_are_summed_once_with_provenance():
    result = aggregate_segment_observations(
        [observation("camera-a", "northbound", 40, 10), observation("camera-b", "southbound", 35, 12)],
        period_start=BASE, period_end=BASE + timedelta(minutes=1),
    )
    assert result.raw_counts["motorcycle"] == 75
    assert result.raw_counts["car"] == 22
    assert result.source_cameras == ("camera-a", "camera-b")
    assert result.source_streams == ("northbound", "southbound")


def test_duplicate_cameras_for_one_stream_are_rejected():
    with pytest.raises(SegmentAggregationError, match="duplicate cameras"):
        aggregate_segment_observations(
            [observation("camera-a", "northbound", 4), observation("camera-b", "northbound", 5)],
            period_start=BASE, period_end=BASE + timedelta(minutes=1),
        )


def test_authoritative_policy_selects_one_camera_per_stream():
    result = aggregate_segment_observations(
        [observation("camera-b", "northbound", 5), observation("camera-a", "northbound", 4)],
        period_start=BASE, period_end=BASE + timedelta(minutes=1),
        aggregation_policy="authoritative_camera",
    )
    assert result.raw_counts["motorcycle"] == 4
    assert result.source_cameras == ("camera-a",)
