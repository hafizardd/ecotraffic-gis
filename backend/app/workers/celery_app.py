from celery import Celery
from app.core.config import settings

redis_url = settings.REDIS_URL

celery_app = Celery(
    "ecotraffic",
    broker=redis_url,
    backend=redis_url,
    include=["app.workers.inference_worker"],
)

celery_app.conf.timezone = "Asia/Jakarta"
celery_app.conf.enable_utc = True
celery_app.conf.broker_connection_retry_on_startup = True


def _get_active_camera_ids() -> list[str]:
    from app.core.database import get_sync_db
    from app.models.camera import Camera
    from sqlalchemy import select

    with get_sync_db() as db:
        cameras = db.execute(
            select(Camera.camera_id).where(Camera.is_active == True)  # noqa: E712
        ).scalars().all()
    return list(cameras)


try:
    celery_app.conf.beat_schedule = {
        f"process_{camera_id}": {
            "task": "app.workers.inference_worker.process_camera",
            "schedule": settings.INTERVAL_SECONDS,
            "args": (camera_id,),
        }
        for camera_id in _get_active_camera_ids()
    }
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Could not load camera schedule: {e}")
    celery_app.conf.beat_schedule = {}