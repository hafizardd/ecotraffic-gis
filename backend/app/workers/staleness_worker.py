"""Periodic staleness sweep that degrades camera status from data age."""

from datetime import datetime, timezone
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.camera import Camera
from app.services.camera_health import CameraHealthPolicy, CameraHealthService, CameraHealthStatus
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

camera_health_service = CameraHealthService(CameraHealthPolicy.from_settings(settings))


@celery_app.task(name="app.workers.staleness_worker.check_camera_staleness")
def check_camera_staleness() -> dict:
    now = datetime.now(timezone.utc)
    degraded = offline = 0
    with get_sync_db() as db:
        cameras = db.execute(
            select(Camera).where(Camera.is_active.is_(True))
        ).scalars().all()
        for camera in cameras:
            previous = camera.status
            updated = camera_health_service.degrade_by_staleness(camera, now)
            if updated is None:
                continue
            if updated is CameraHealthStatus.OFFLINE:
                offline += 1
            else:
                degraded += 1
            logger.info(
                "camera_status_degraded_by_staleness",
                extra={
                    "camera_id": camera.camera_id,
                    "previous_status": previous,
                    "new_status": updated.value,
                },
            )
    return {"degraded": degraded, "offline": offline}
