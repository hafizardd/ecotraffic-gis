from celery import Celery
from app.core.config import settings

redis_url = settings.REDIS_URL

celery_app = Celery(
    "ecotraffic",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.workers.segment_calculation_worker",
        "app.workers.snapshot_worker",
    ],
)

celery_app.conf.timezone = "Asia/Jakarta"
celery_app.conf.enable_utc = True
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600
celery_app.conf.task_routes = {
    "app.workers.segment_calculation_worker.recalculate_segment_emissions": {"queue": "inference"},
    "app.workers.snapshot_worker.sample_historical_cameras": {"queue": "snapshot"},
}

celery_app.conf.beat_schedule = {
    "recalculate-segment-emissions": {
        "task": "app.workers.segment_calculation_worker.recalculate_segment_emissions",
        "schedule": settings.SEGMENT_OBSERVATION_WINDOW_SECONDS,
    },
    # 5-min beat; per-camera cadence follows next_sample_at (claim-lease).
    "snapshot-historical": {
        "task": "app.workers.snapshot_worker.sample_historical_cameras",
        "schedule": 60,
    },
}
