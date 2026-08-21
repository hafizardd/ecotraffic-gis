from datetime import datetime, timezone
import logging

from sqlalchemy import case, select, update

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.camera import Camera
from app.services.camera_scheduler import CameraSchedulingPolicy, plan_due_cameras
from app.workers.celery_app import celery_app


logger = logging.getLogger(__name__)

PROCESS_CAMERA_TASK = "app.workers.inference_worker.process_camera"


def _mark_camera_due_again(camera_id: str, now: datetime) -> None:
    with get_sync_db() as db:
        db.execute(
            update(Camera)
            .where(Camera.camera_id == camera_id)
            .values(next_sample_at=now)
        )


@celery_app.task(name="app.workers.scheduler.dispatch_due_cameras")
def dispatch_due_cameras() -> dict[str, int]:
    """Select due cameras and enqueue their existing processing tasks.

    This task intentionally does not acquire frames, run inference, calculate
    emissions, or write emission history.
    """

    now = datetime.now(timezone.utc)
    policy = CameraSchedulingPolicy.from_settings(settings)
    priority_order = case(
        (Camera.priority == "high", 0),
        (Camera.priority == "medium", 1),
        (Camera.priority == "low", 2),
        else_=1,
    )

    with get_sync_db() as db:
        cameras = db.execute(
            select(Camera)
            .where(Camera.is_active.is_(True))
            .order_by(priority_order, Camera.next_sample_at.nullsfirst(), Camera.camera_id)
            .with_for_update(skip_locked=True)
        ).scalars().all()
        plan = plan_due_cameras(cameras, now, policy)

    enqueued_count = 0
    failed_count = 0
    for scheduled_camera in plan.due_cameras:
        try:
            celery_app.send_task(PROCESS_CAMERA_TASK, args=(scheduled_camera.camera_id,))
            enqueued_count += 1
        except Exception:
            failed_count += 1
            _mark_camera_due_again(scheduled_camera.camera_id, now)
            logger.exception(
                "camera_schedule_enqueue_failed",
                extra={"camera_id": scheduled_camera.camera_id},
            )

    logger.info(
        "camera_scheduler_run",
        extra={
            "initialized_count": plan.initialized_count,
            "due_count": len(plan.due_cameras),
            "enqueued_count": enqueued_count,
            "failed_count": failed_count,
        },
    )
    return {
        "initialized_count": plan.initialized_count,
        "enqueued_count": enqueued_count,
        "failed_count": failed_count,
    }
