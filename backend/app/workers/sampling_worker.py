from datetime import datetime, timezone
import logging
import uuid

import redis

from app.core.config import settings
from app.services.camera_management import get_active_camera_source
from app.services.inference_jobs import InferenceJob, normalize_job_priority
from app.services.inference_queue import InferenceQueue, ReservationStatus
from app.workers.celery_app import celery_app
from cv.frame_sampler import FrameCaptureError, FrameSampler
from cv.frame_store import FrameEncodingError, RedisFrameStore


logger = logging.getLogger(__name__)

SAMPLE_CAMERA_TASK = "app.workers.sampling_worker.sample_camera"
LEGACY_PROCESS_CAMERA_TASK = "app.workers.inference_worker.process_camera"
INFERENCE_TASK = "app.workers.inference_worker.process_inference_job"

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
frame_sampler = FrameSampler(
    open_timeout_seconds=settings.FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS,
    read_timeout_seconds=settings.FRAME_CAPTURE_READ_TIMEOUT_SECONDS,
    ffmpeg_timeout_seconds=settings.FRAME_FFMPEG_TIMEOUT_SECONDS,
)


def _queue_depth_or_unknown() -> int:
    try:
        return inference_queue.depth()
    except Exception:
        logger.warning("inference_queue_depth_unavailable", exc_info=True)
        return -1


def _sample_and_enqueue(task, camera_id: str) -> dict:
    camera = get_active_camera_source(camera_id)
    if camera is None:
        logger.warning(
            "camera_sampling_skipped",
            extra={"camera_id": camera_id, "reason": "missing_or_inactive"},
        )
        return {"camera_id": camera_id, "status": "missing_or_inactive"}

    job_id = str(uuid.uuid4())
    reservation = inference_queue.reserve(camera.camera_id, job_id)
    if reservation is not ReservationStatus.ACCEPTED:
        queue_depth = _queue_depth_or_unknown()
        logger.warning(
            "camera_sampling_not_reserved",
            extra={
                "camera_id": camera.camera_id,
                "job_id": job_id,
                "reason": reservation.value,
                "queue_depth": queue_depth,
            },
        )
        return {
            "camera_id": camera.camera_id,
            "job_id": job_id,
            "status": reservation.value,
            "queue_depth": queue_depth,
        }

    stored_frame = None
    try:
        captured_frame = frame_sampler.capture(camera.stream_url, camera.referer)
        stored_frame = frame_store.store(job_id, captured_frame.frame)
        job = InferenceJob(
            job_id=job_id,
            camera_id=camera.camera_id,
            camera_database_id=str(camera.id),
            captured_at=captured_frame.captured_at,
            enqueued_at=datetime.now(timezone.utc),
            priority=normalize_job_priority(camera.priority),
            sampling_interval_seconds=camera.sampling_interval_seconds,
            frame_key=stored_frame.key,
            frame_size_bytes=stored_frame.size_bytes,
            frame_acquisition_latency_s=captured_frame.acquisition_latency_s,
            frame_capture_method=captured_frame.method,
        )
        celery_app.send_task(
            INFERENCE_TASK,
            kwargs={"job_payload": job.to_payload()},
            queue="inference",
            priority=job.celery_priority,
        )
    except FrameCaptureError as exc:
        inference_queue.release(camera.camera_id, job_id)
        logger.warning(
            "camera_sampling_capture_failed",
            extra={"camera_id": camera.camera_id, "job_id": job_id},
        )
        raise task.retry(exc=exc, countdown=15)
    except FrameEncodingError:
        inference_queue.release(camera.camera_id, job_id)
        logger.exception(
            "camera_sampling_frame_rejected",
            extra={"camera_id": camera.camera_id, "job_id": job_id},
        )
        return {
            "camera_id": camera.camera_id,
            "job_id": job_id,
            "status": "frame_rejected",
        }
    except Exception as exc:
        if stored_frame is not None:
            frame_store.delete(stored_frame.key)
        inference_queue.release(camera.camera_id, job_id)
        logger.exception(
            "camera_sampling_enqueue_failed",
            extra={"camera_id": camera.camera_id, "job_id": job_id},
        )
        raise task.retry(exc=exc, countdown=5)

    queue_depth = _queue_depth_or_unknown()
    logger.info(
        "inference_job_enqueued",
        extra={
            "camera_id": camera.camera_id,
            "job_id": job_id,
            "captured_at": captured_frame.captured_at.isoformat(),
            "frame_acquisition_latency_s": round(
                captured_frame.acquisition_latency_s,
                3,
            ),
            "frame_size_bytes": stored_frame.size_bytes,
            "queue_depth": queue_depth,
            "priority": job.priority,
        },
    )
    return {
        "camera_id": camera.camera_id,
        "job_id": job_id,
        "status": "queued",
        "queue_depth": queue_depth,
    }


@celery_app.task(bind=True, name=SAMPLE_CAMERA_TASK, max_retries=3)
def sample_camera(self, camera_id: str) -> dict:
    return _sample_and_enqueue(self, camera_id)


@celery_app.task(bind=True, name=LEGACY_PROCESS_CAMERA_TASK, max_retries=3)
def process_camera(self, camera_id: str) -> dict:
    """Backward-compatible task name for callers using the previous worker API."""

    return _sample_and_enqueue(self, camera_id)
