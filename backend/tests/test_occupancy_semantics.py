from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from cv.detector import VehicleDetector


class _FakeModel:
    names = {0: "car", 1: "motorcycle", 2: "bus", 3: "truck"}


def _fake_detector() -> VehicleDetector:
    return VehicleDetector(model_factory=lambda path: _FakeModel())


def _box(cls_id: int, xyxy, conf: float = 0.9):
    return SimpleNamespace(cls=np.array([cls_id]), conf=np.array([conf]), xyxy=np.array([xyxy]))


def test_parse_result_for_camera_uses_whole_frame_without_roi():
    detector = _fake_detector()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    result = SimpleNamespace(boxes=[_box(0, [80, 0, 100, 10])])

    assert detector.parse_result_for_camera(frame, result, None)["car"] == 1


def test_parse_result_for_camera_filters_outside_roi():
    detector = _fake_detector()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    outside = SimpleNamespace(boxes=[_box(0, [80, 0, 100, 10])])
    inside = SimpleNamespace(boxes=[_box(0, [40, 80, 60, 100])])

    assert detector.parse_result_for_camera(frame, outside, "atcs_jlagran")["car"] == 0
    assert detector.parse_result_for_camera(frame, inside, "atcs_jlagran")["car"] == 1


def test_snapshot_occupancy_is_estimated_as_hourly_volume():
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
    assert result["volume_per_hour"]["car"] == 240.0
    assert result["vkt_km_h"]["car"] == 240.0
    assert result["volume_status"] == "estimated"
    assert result["emissions"]["totals_g_h"]
