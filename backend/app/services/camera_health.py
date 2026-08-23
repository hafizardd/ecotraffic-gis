"""Camera sampling health state and bounded retry scheduling."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import select

from app.core.database import get_sync_db
from app.models.camera import Camera


class CameraHealthStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass(frozen=True, slots=True)
class CameraHealthPolicy:
    retry_base_seconds: int
    retry_max_seconds: int
    failures_before_offline: int

    def __post_init__(self) -> None:
        if self.retry_base_seconds <= 0:
            raise ValueError("retry_base_seconds must be greater than zero")
        if self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("retry_max_seconds must be at least retry_base_seconds")
        if self.failures_before_offline <= 0:
            raise ValueError("failures_before_offline must be greater than zero")

    @classmethod
    def from_settings(cls, settings: Any) -> "CameraHealthPolicy":
        return cls(
            retry_base_seconds=settings.CAMERA_RETRY_BASE_SECONDS,
            retry_max_seconds=settings.CAMERA_RETRY_MAX_SECONDS,
            failures_before_offline=settings.CAMERA_FAILURES_BEFORE_OFFLINE,
        )

    def retry_delay_seconds(self, failure_count: int) -> int:
        if failure_count <= 0:
            return 0
        return min(
            self.retry_base_seconds * (2 ** (failure_count - 1)),
            self.retry_max_seconds,
        )

    def status_for_failure_count(self, failure_count: int) -> CameraHealthStatus:
        if failure_count >= self.failures_before_offline:
            return CameraHealthStatus.OFFLINE
        return CameraHealthStatus.DEGRADED


@dataclass(frozen=True, slots=True)
class CameraFailureUpdate:
    failure_count: int
    status: CameraHealthStatus
    retry_delay_seconds: int
    next_sample_at: datetime


class CameraHealthService:
    """Persist capture outcomes without affecting other camera schedules."""

    def __init__(self, policy: CameraHealthPolicy) -> None:
        self.policy = policy

    def record_capture_success(
        self,
        camera_database_id: str | uuid.UUID,
        now: datetime,
    ) -> None:
        with get_sync_db() as db:
            camera = self._locked_camera(db, camera_database_id)
            if camera is None:
                return
            camera.last_sample_at = now
            camera.last_success_at = now
            camera.failure_count = 0
            camera.status = CameraHealthStatus.ACTIVE.value

    def record_capture_failure(
        self,
        camera_database_id: str | uuid.UUID,
        now: datetime,
    ) -> CameraFailureUpdate | None:
        with get_sync_db() as db:
            camera = self._locked_camera(db, camera_database_id)
            if camera is None:
                return None
            failure_count = int(camera.failure_count) + 1
            retry_delay_seconds = self.policy.retry_delay_seconds(failure_count)
            status = self.policy.status_for_failure_count(failure_count)
            next_sample_at = now + timedelta(seconds=retry_delay_seconds)
            camera.last_sample_at = now
            camera.last_error_at = now
            camera.failure_count = failure_count
            camera.status = status.value
            camera.next_sample_at = next_sample_at
            return CameraFailureUpdate(
                failure_count=failure_count,
                status=status,
                retry_delay_seconds=retry_delay_seconds,
                next_sample_at=next_sample_at,
            )

    @staticmethod
    def _locked_camera(db, camera_database_id: str | uuid.UUID) -> Camera | None:
        return db.execute(
            select(Camera)
            .where(Camera.id == uuid.UUID(str(camera_database_id)))
            .with_for_update()
        ).scalar_one_or_none()
