from celery import Celery
from app.core.config import settings

redis_url = settings.REDIS_URL

celery_app = Celery(
    "ecotraffic",
    broker=redis_url,
    backend=redis_url,
    include=["app.workers.scheduler"],
)

celery_app.conf.timezone = "Asia/Jakarta"
celery_app.conf.enable_utc = True
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600
celery_app.conf.task_queue_max_priority = 9
celery_app.conf.task_default_priority = 5
celery_app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "queue_order_strategy": "priority",
}
celery_app.conf.task_routes = {
    "app.workers.scheduler.dispatch_due_cameras": {"queue": "camera_sampling"},
    "app.workers.sampling_worker.sample_camera": {"queue": "camera_sampling"},
    "app.workers.inference_worker.process_camera": {"queue": "camera_sampling"},
    "app.workers.inference_worker.process_inference_job": {"queue": "inference"},
}

celery_app.conf.beat_schedule = {
    "dispatch_due_cameras": {
        "task": "app.workers.scheduler.dispatch_due_cameras",
        "schedule": settings.CAMERA_SCHEDULER_TICK_SECONDS,
    },
}
