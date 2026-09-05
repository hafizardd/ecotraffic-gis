from datetime import datetime, timezone

import pytest

from app.services.segment_mapping import (
    CameraSegmentMapping,
    MappingResolutionError,
    resolve_camera_mapping,
)


CAPTURED_AT = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)


def test_resolves_active_mapping_for_camera_and_time():
    mapping = CameraSegmentMapping("camera-a", "segment-1", "northbound")
    assert resolve_camera_mapping([mapping], camera_id="camera-a", captured_at=CAPTURED_AT) == mapping


def test_missing_or_inactive_mapping_is_rejected():
    mapping = CameraSegmentMapping("camera-a", "segment-1", "northbound", is_active=False)
    with pytest.raises(MappingResolutionError, match="no active"):
        resolve_camera_mapping([mapping], camera_id="camera-a", captured_at=CAPTURED_AT)


def test_ambiguous_active_mapping_is_rejected():
    mappings = [
        CameraSegmentMapping("camera-a", "segment-1", "northbound"),
        CameraSegmentMapping("camera-a", "segment-2", "southbound"),
    ]
    with pytest.raises(MappingResolutionError, match="ambiguous"):
        resolve_camera_mapping(mappings, camera_id="camera-a", captured_at=CAPTURED_AT)
