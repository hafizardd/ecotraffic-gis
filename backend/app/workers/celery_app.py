from celery import Celery
from app.core.config import settings

redis_url = settings.REDIS_URL

celery_app = Celery(
    "ecotraffic",
    broker=redis_url,
    backend=redis_url,
    include=["app.workers.scheduler", "app.workers.inference_worker"],
)

celery_app.conf.timezone = "Asia/Jakarta"
celery_app.conf.enable_utc = True
celery_app.conf.broker_connection_retry_on_startup = True

celery_app.conf.beat_schedule = {
    "dispatch_due_cameras": {
        "task": "app.workers.scheduler.dispatch_due_cameras",
        "schedule": settings.CAMERA_SCHEDULER_TICK_SECONDS,
    },
}
