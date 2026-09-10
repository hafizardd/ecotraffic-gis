"""Snapshot sampler scheduling and duplicate-stream selection helpers."""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.workers.snapshot_worker import _effective_interval, _select_stream_observations
from cv.proposal_emission_factors import VEHICLE_CATEGORIES

BASE = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
COUNTS = {category: 1 for category in VEHICLE_CATEGORIES}


def _item(camera_id: str, captured_at: datetime, stream: str = "default"):
    observation = SegmentTrafficObservation(
        camera_id, "SEG", stream, captured_at, 300, COUNTS,
        vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY,
    )
    return (observation, None, True)


def test_effective_interval_follows_priority():
    assert _effective_interval("high", None) == settings.SNAPSHOT_HIGH_INTERVAL_SECONDS
    assert _effective_interval("medium", None) == settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS
    assert _effective_interval("low", None) == settings.SNAPSHOT_LOW_INTERVAL_SECONDS
    assert _effective_interval(None, None) == settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS


def test_effective_interval_per_camera_override_wins():
    assert _effective_interval("high", 42) == 42


def test_duplicate_stream_keeps_latest_camera():
    earlier = _item("camera-a", BASE)
    later = _item("camera-b", BASE + timedelta(seconds=10))
    selected, dropped = _select_stream_observations([earlier, later])
    assert [item[0].camera_id for item in selected] == ["camera-b"]
    assert dropped == {"default": ["camera-a"]}


def test_duplicate_stream_tie_breaks_smallest_camera_id():
    first = _item("camera-b", BASE)
    second = _item("camera-a", BASE)
    selected, dropped = _select_stream_observations([first, second])
    assert [item[0].camera_id for item in selected] == ["camera-a"]
    assert dropped == {"default": ["camera-b"]}


def test_single_camera_stream_is_untouched():
    selected, dropped = _select_stream_observations([_item("camera-a", BASE), _item("camera-a", BASE + timedelta(seconds=5))])
    assert len(selected) == 2
    assert dropped == {}
