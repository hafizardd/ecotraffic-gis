from dataclasses import dataclass
import uuid

from sqlalchemy import select

from app.core.database import get_sync_db
from app.models.camera import Camera


@dataclass(frozen=True, slots=True)
class CameraSource:
    """Processing-safe camera data detached from the ORM session."""

    id: uuid.UUID
    camera_id: str
    stream_url: str
    referer: str | None
    priority: str
    sampling_interval_seconds: int | None


def get_active_camera_source(camera_id: str) -> CameraSource | None:
    """Return the active camera source needed by processing workers."""

    with get_sync_db() as db:
        camera = db.execute(
            select(Camera).where(Camera.camera_id == camera_id)
        ).scalars().first()

        if camera is None or not camera.is_active:
            return None

        return CameraSource(
            id=camera.id,
            camera_id=camera.camera_id,
            stream_url=camera.stream_url,
            referer=camera.referer,
            priority=camera.priority,
            sampling_interval_seconds=camera.sampling_interval_seconds,
        )
