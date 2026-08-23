from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services.camera_scheduler import (
    CameraSchedulingPolicy,
    initial_stagger_seconds,
    plan_due_cameras,
)


@dataclass
class _Camera:
    camera_id: str
    priority: str = "medium"
    sampling_interval_seconds: int | None = None
    next_sample_at: datetime | None = None
    is_active: bool = True


POLICY = CameraSchedulingPolicy(
    high_interval_seconds=10,
    medium_interval_seconds=30,
    low_interval_seconds=60,
    max_dispatch_per_tick=2,
)


def test_unscheduled_cameras_receive_deterministic_staggered_due_times():
    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    cameras = [
        _Camera("camera-alpha"),
        _Camera("camera-bravo"),
        _Camera("camera-charlie"),
    ]

    plan = plan_due_cameras(cameras, now, POLICY)

    assert plan.initialized_count == 3
    assert plan.due_cameras == ()
    offsets = [(camera.next_sample_at - now).total_seconds() for camera in cameras]
    assert len(set(offsets)) == len(cameras)
    assert all(0 <= offset < POLICY.medium_interval_seconds for offset in offsets)


def test_due_cameras_are_priority_ordered_and_bounded():
    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    cameras = [
        _Camera("camera-low", priority="low", next_sample_at=now - timedelta(seconds=1)),
        _Camera("camera-medium", next_sample_at=now - timedelta(seconds=1)),
        _Camera("camera-high", priority="high", next_sample_at=now - timedelta(seconds=1)),
    ]

    plan = plan_due_cameras(cameras, now, POLICY)

    assert [camera.camera_id for camera in plan.due_cameras] == [
        "camera-high",
        "camera-medium",
    ]
    assert cameras[0].next_sample_at == now - timedelta(seconds=1)
    assert cameras[1].next_sample_at == now + timedelta(seconds=29)
    assert cameras[2].next_sample_at == now + timedelta(seconds=9)


def test_not_due_and_inactive_cameras_are_not_enqueued():
    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    future_camera = _Camera("camera-future", next_sample_at=now + timedelta(seconds=1))
    inactive_camera = _Camera(
        "camera-inactive",
        next_sample_at=now - timedelta(seconds=1),
        is_active=False,
    )

    plan = plan_due_cameras([future_camera, inactive_camera], now, POLICY)

    assert plan.initialized_count == 0
    assert plan.due_cameras == ()
    assert future_camera.next_sample_at == now + timedelta(seconds=1)
    assert inactive_camera.next_sample_at == now - timedelta(seconds=1)


def test_per_camera_interval_overrides_priority_default():
    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    camera = _Camera(
        "camera-custom",
        priority="low",
        sampling_interval_seconds=7,
        next_sample_at=now - timedelta(seconds=1),
    )

    plan = plan_due_cameras([camera], now, POLICY)

    assert [scheduled.camera_id for scheduled in plan.due_cameras] == ["camera-custom"]
    assert camera.next_sample_at == now + timedelta(seconds=6)


def test_stagger_is_stable_and_within_the_camera_interval():
    first = initial_stagger_seconds("camera-12", 60)
    second = initial_stagger_seconds("camera-12", 60)

    assert first == second
    assert 0 <= first < 60
