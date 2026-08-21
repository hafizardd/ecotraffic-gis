from datetime import datetime, timezone
import json
import logging
import os
import time
import uuid

import redis
from celery.signals import worker_init, worker_shutdown

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.emission import Emission
from app.services.detector_lifecycle import DetectorLifecycle
from app.services.inference_jobs import InferenceJob
from app.services.inference_queue import InferenceQueue
from app.workers.celery_app import celery_app
from cv.detector import VehicleDetector
from cv.emission_factors import calculate_emission
from cv.frame_store import RedisFrameStore


logger = logging.getLogger(__name__)

INFERENCE_TASK = "app.workers.inference_worker.process_inference_job"


def _build_detector() -> VehicleDetector:
    return VehicleDetector(
        model_path=settings.YOLO_MODEL_PATH,
        confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        device=settings.YOLO_DEVICE,
        image_size=settings.YOLO_IMAGE_SIZE,
    )


detector_lifecycle = DetectorLifecycle(_build_detector)


def _uses_solo_pool(sender) -> bool:
    pool_class = getattr(sender, "pool_cls", None)
    if isinstance(pool_class, str):
        return pool_class.lower().split(".")[-1] == "solo"

    pool_module = getattr(pool_class, "__module__", "").lower()
    return pool_module == "celery.concurrency.solo"


@worker_init.connect(weak=False)
def initialize_inference_worker_detector(sender=None, **_kwargs) -> None:
    """Eagerly load one model in the deployed solo inference process."""
    if not _uses_solo_pool(sender):
        logger.info(
            "yolo_model_initialization_deferred",
            extra={"process_id": os.getpid()},
        )
        return

    detector_lifecycle.start()
    logger.info(
        "inference_worker_detector_ready",
        extra={"process_id": os.getpid()},
    )


@worker_shutdown.connect(weak=False)
def shutdown_inference_worker_detector(**_kwargs) -> None:
    detector_lifecycle.stop()
    logger.info(
        "inference_worker_detector_released",
        extra={"process_id": os.getpid()},
    )


redis_client = redis.Redis.from_url(settings.REDIS_URL)
inference_queue = InferenceQueue(
    redis_client,
    max_pending=settings.INFERENCE_QUEUE_MAX_PENDING,
    reservation_ttl_seconds=settings.INFERENCE_RESERVATION_TTL_SECONDS,
)
frame_store = RedisFrameStore(
    redis_client,
    ttl_seconds=settings.INFERENCE_FRAME_TTL_SECONDS,
    max_bytes=settings.INFERENCE_FRAME_MAX_BYTES,
    jpeg_quality=settings.INFERENCE_JPEG_QUALITY,
)


def publish_to_redis(camera_id: str, payload: dict) -> None:
    redis_client.publish(f"emissions:{camera_id}", json.dumps(payload))


def _cleanup_job(job: InferenceJob) -> None:
    try:
        frame_store.delete(job.frame_key)
    finally:
        inference_queue.release(job.camera_id, job.job_id)


def _queue_depth_or_unknown() -> int:
    try:
        return inference_queue.depth()
    except Exception:
        logger.warning("inference_queue_depth_unavailable", exc_info=True)
        return -1


@celery_app.task(
    bind=True,
    name=INFERENCE_TASK,
    max_retries=settings.INFERENCE_MAX_RETRIES,
    soft_time_limit=settings.INFERENCE_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.INFERENCE_TASK_TIME_LIMIT_SECONDS,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_inference_job(self, job_payload: dict) -> dict:
    """Decode one queued frame, run inference, persist, and publish its result."""

    job = InferenceJob.from_payload(job_payload)
    inference_started_at = time.monotonic()
    queue_wait_s = max(
        0.0,
        (datetime.now(timezone.utc) - job.enqueued_at).total_seconds(),
    )

    try:
        frame = frame_store.load(job.frame_key)
    except Exception:
        _cleanup_job(job)
        logger.exception(
            "inference_frame_load_failed",
            extra={"camera_id": job.camera_id, "job_id": job.job_id},
        )
        raise

    try:
        vehicle_counts, _ = detector_lifecycle.detect(frame)
    except Exception as exc:
        if self.request.retries < self.max_retries:
            retry_countdown = 2 ** (self.request.retries + 1)
            logger.warning(
                "inference_job_retrying",
                extra={
                    "camera_id": job.camera_id,
                    "job_id": job.job_id,
                    "retry_count": self.request.retries + 1,
                    "retry_countdown_s": retry_countdown,
                },
            )
            raise self.retry(exc=exc, countdown=retry_countdown)

        _cleanup_job(job)
        logger.exception(
            "inference_job_failed",
            extra={"camera_id": job.camera_id, "job_id": job.job_id},
        )
        raise

    try:
        emission = calculate_emission(vehicle_counts)
    except Exception:
        _cleanup_job(job)
        logger.exception(
            "inference_emission_calculation_failed",
            extra={"camera_id": job.camera_id, "job_id": job.job_id},
        )
        raise
    inference_latency_s = time.monotonic() - inference_started_at
    cycle_duration_s = job.frame_acquisition_latency_s + inference_latency_s
    processed_at = datetime.now(timezone.utc)
    result = {
        "camera_id": job.camera_id,
        "timestamp": processed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "captured_at": job.captured_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frame_acquisition_latency_s": round(job.frame_acquisition_latency_s, 3),
        "queue_wait_s": round(queue_wait_s, 3),
        "inference_latency_s": round(inference_latency_s, 3),
        "job_id": job.job_id,
        "car": vehicle_counts["car"],
        "motorcycle": vehicle_counts["motorcycle"],
        "bus": vehicle_counts["bus"],
        "truck": vehicle_counts["truck"],
        "total_co_g_per_min": emission["total_co_g_per_min"],
        "total_co_kg_per_hr": emission["total_co_kg_per_hr"],
        "total_nox_g_per_min": emission["total_nox_g_per_min"],
        "total_nox_kg_per_hr": emission["total_nox_kg_per_hr"],
        "total_pm_g_per_min": emission["total_pm_g_per_min"],
        "total_pm_kg_per_hr": emission["total_pm_kg_per_hr"],
        "total_nmvoc_g_per_min": emission["total_nmvoc_g_per_min"],
        "total_nmvoc_kg_per_hr": emission["total_nmvoc_kg_per_hr"],
        "cycle_duration_s": round(cycle_duration_s, 2),
    }

    try:
        with get_sync_db() as db:
            db.add(
                Emission(
                    id=uuid.uuid4(),
                    camera_id=uuid.UUID(job.camera_database_id),
                    timestamp=processed_at,
                    car=vehicle_counts["car"],
                    motorcycle=vehicle_counts["motorcycle"],
                    bus=vehicle_counts["bus"],
                    truck=vehicle_counts["truck"],
                    total_co_g_per_min=emission["total_co_g_per_min"],
                    total_co_kg_per_hr=emission["total_co_kg_per_hr"],
                    total_nox_g_per_min=emission["total_nox_g_per_min"],
                    total_nox_kg_per_hr=emission["total_nox_kg_per_hr"],
                    total_pm_g_per_min=emission["total_pm_g_per_min"],
                    total_pm_kg_per_hr=emission["total_pm_kg_per_hr"],
                    total_nmvoc_g_per_min=emission["total_nmvoc_g_per_min"],
                    total_nmvoc_kg_per_hr=emission["total_nmvoc_kg_per_hr"],
                    cycle_duration_s=round(cycle_duration_s, 2),
                )
            )
        publish_to_redis(job.camera_id, result)
    finally:
        _cleanup_job(job)

    logger.info(
        "inference_job_completed",
        extra={
            "camera_id": job.camera_id,
            "job_id": job.job_id,
            "captured_at": job.captured_at.isoformat(),
            "queue_wait_s": round(queue_wait_s, 3),
            "inference_latency_s": round(inference_latency_s, 3),
            "queue_depth": _queue_depth_or_unknown(),
        },
    )
    return result
