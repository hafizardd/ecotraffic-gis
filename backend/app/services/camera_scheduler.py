from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from typing import Iterable, Protocol


PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


class SchedulableCamera(Protocol):
    camera_id: str
    is_active: bool
    priority: str
    sampling_interval_seconds: int | None
    next_sample_at: datetime | None


@dataclass(frozen=True, slots=True)
class CameraSchedulingPolicy:
    high_interval_seconds: int
    medium_interval_seconds: int
    low_interval_seconds: int
    max_dispatch_per_tick: int

    @classmethod
    def from_settings(cls, settings) -> "CameraSchedulingPolicy":
        return cls(
            high_interval_seconds=settings.CAMERA_HIGH_INTERVAL_SECONDS,
            medium_interval_seconds=settings.CAMERA_MEDIUM_INTERVAL_SECONDS,
            low_interval_seconds=settings.CAMERA_LOW_INTERVAL_SECONDS,
            max_dispatch_per_tick=settings.CAMERA_SCHEDULER_MAX_DISPATCH_PER_TICK,
        )

    def interval_for(self, camera: SchedulableCamera) -> int:
        configured_interval = camera.sampling_interval_seconds
        if configured_interval is not None and configured_interval > 0:
            return configured_interval

        priority = normalize_priority(camera.priority)
        return {
            "high": self.high_interval_seconds,
            "medium": self.medium_interval_seconds,
            "low": self.low_interval_seconds,
        }[priority]


@dataclass(frozen=True, slots=True)
class ScheduledCamera:
    camera_id: str
    priority: str


@dataclass(frozen=True, slots=True)
class CameraSchedulePlan:
    initialized_count: int
    due_cameras: tuple[ScheduledCamera, ...]


def normalize_priority(priority: str | None) -> str:
    normalized = (priority or "medium").lower()
    return normalized if normalized in PRIORITY_RANK else "medium"


def initial_stagger_seconds(camera_id: str, interval_seconds: int) -> int:
    """Return a stable offset so a new camera does not join a burst."""

    digest = hashlib.blake2s(camera_id.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, byteorder="big") % interval_seconds


def next_due_after(
    previous_due_at: datetime,
    now: datetime,
    interval_seconds: int,
) -> datetime:
    """Advance a camera without losing its established schedule offset."""

    next_due_at = previous_due_at
    interval = timedelta(seconds=interval_seconds)
    while next_due_at <= now:
        next_due_at += interval
    return next_due_at


def plan_due_cameras(
    cameras: Iterable[SchedulableCamera],
    now: datetime,
    policy: CameraSchedulingPolicy,
) -> CameraSchedulePlan:
    """Initialize unscheduled cameras and select a bounded, priority-ordered batch."""

    initialized_count = 0
    due_candidates: list[tuple[int, datetime, SchedulableCamera, int]] = []

    for camera in cameras:
        if not camera.is_active:
            continue

        interval_seconds = policy.interval_for(camera)
        if camera.next_sample_at is None:
            camera.next_sample_at = now + timedelta(
                seconds=initial_stagger_seconds(camera.camera_id, interval_seconds)
            )
            initialized_count += 1
            continue

        if camera.next_sample_at <= now:
            due_candidates.append(
                (
                    PRIORITY_RANK[normalize_priority(camera.priority)],
                    camera.next_sample_at,
                    camera,
                    interval_seconds,
                )
            )

    due_candidates.sort(key=lambda item: (item[0], item[1], item[2].camera_id))

    due_cameras: list[ScheduledCamera] = []
    for _, previous_due_at, camera, interval_seconds in due_candidates[
        : policy.max_dispatch_per_tick
    ]:
        camera.next_sample_at = next_due_after(
            previous_due_at,
            now,
            interval_seconds,
        )
        due_cameras.append(
            ScheduledCamera(
                camera_id=camera.camera_id,
                priority=normalize_priority(camera.priority),
            )
        )

    return CameraSchedulePlan(
        initialized_count=initialized_count,
        due_cameras=tuple(due_cameras),
    )
