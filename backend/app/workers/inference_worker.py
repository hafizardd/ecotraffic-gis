from collections.abc import Sequence
from datetime import datetime, timezone
import json
import logging
import os
import time

import redis
from celery.signals import worker_init, worker_shutdown

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_emission_store import persist_segment_emission_sync
from app.services.segment_mapping import MappingResolutionError, CameraSegmentMapping, resolve_camera_mapping
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.services.segment_observation_store import observation_row
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from app.services.detector_lifecycle import DetectorLifecycle
from app.services.data_freshness import FreshnessPolicy
from app.services.emission_aggregation import (
    AggregationUpdate,
    EmissionObservation,
    EmissionWindowAggregator,
)
from app.services.inference_batcher import InferenceBatcher
from app.services.inference_jobs import InferenceJob
from app.services.inference_queue import InferenceQueue
from app.services.historical_emission_store import HistoricalEmissionStore
from app.services.latest_emission_state import LatestEmissionStateStore
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


def _detect_batch(frames: Sequence):
    return detector_lifecycle.detect_batch(frames, annotate=False)


inference_batcher = InferenceBatcher(
    _detect_batch,
    max_batch_size=settings.INFERENCE_MAX_BATCH_SIZE,
    max_wait_ms=settings.INFERENCE_MAX_BATCH_WAIT_MS,
)
emission_aggregator = EmissionWindowAggregator(
    window_seconds=settings.EMISSION_AGGREGATION_WINDOW_SECONDS,
)


def _uses_in_process_pool(sender) -> bool:
    pool_class = getattr(sender, "pool_cls", None)
    if isinstance(pool_class, str):
        return pool_class.lower().split(".")[-1] in {"solo", "threads"}

    pool_module = getattr(pool_class, "__module__", "").lower()
    return pool_module in {
        "celery.concurrency.solo",
        "celery.concurrency.thread",
    }


@worker_init.connect(weak=False)
def initialize_inference_worker_detector(sender=None, **_kwargs) -> None:
    """Eagerly start the model and micro-batcher for in-process pools."""
    if not _uses_in_process_pool(sender):
        logger.info(
            "yolo_model_initialization_deferred",
            extra={"process_id": os.getpid()},
        )
        return

    detector_lifecycle.start()
    inference_batcher.start()
    logger.info(
        "inference_worker_detector_ready",
        extra={
            "process_id": os.getpid(),
            "max_batch_size": settings.INFERENCE_MAX_BATCH_SIZE,
            "max_batch_wait_ms": settings.INFERENCE_MAX_BATCH_WAIT_MS,
        },
    )


@worker_shutdown.connect(weak=False)
def shutdown_inference_worker_detector(**_kwargs) -> None:
    inference_batcher.stop()
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
latest_state_store = LatestEmissionStateStore(
    redis_client,
    ttl_seconds=settings.LATEST_EMISSION_STATE_TTL_SECONDS,
    freshness_policy=FreshnessPolicy.from_settings(settings),
)
historical_emission_store = HistoricalEmissionStore()

_segment_mappings: tuple[float, list[CameraSegmentMapping]] | None = None


def _load_segment_mappings() -> list[CameraSegmentMapping]:
    global _segment_mappings
    now = time.monotonic()
    if _segment_mappings is not None and now - _segment_mappings[0] < settings.SEGMENT_MAPPING_CACHE_TTL_SECONDS:
        return _segment_mappings[1]
    with get_sync_db() as db:
        rows = db.execute(
            __import__("sqlalchemy").select(
                __import__("app.models.camera", fromlist=["Camera"]).Camera.camera_id,
                RoadSegment.road_segment_id, CameraRoadSegment.lane_or_stream_id,
                CameraRoadSegment.is_active, CameraRoadSegment.valid_from, CameraRoadSegment.valid_to,
            ).join(CameraRoadSegment, CameraRoadSegment.camera_id == __import__("app.models.camera", fromlist=["Camera"]).Camera.id)
            .join(RoadSegment, CameraRoadSegment.road_segment_id == RoadSegment.id)
            .where(CameraRoadSegment.is_active.is_(True))
        ).all()
    _segment_mappings = (now, [CameraSegmentMapping(*row) for row in rows])
    return _segment_mappings[1]


def _persist_segment_observation(job: InferenceJob, vehicle_counts: dict[str, int]) -> dict:
    metadata = {"segment_pipeline_status": "not_attempted"}
    try:
        mapping = resolve_camera_mapping(_load_segment_mappings(), camera_id=job.camera_id, captured_at=job.captured_at)
    except MappingResolutionError:
        metadata["segment_pipeline_status"] = "no_mapping"
        return metadata
    observation = SegmentTrafficObservation(
        camera_id=job.camera_id, road_segment_id=mapping.road_segment_id,
        lane_or_stream_id=mapping.lane_or_stream_id, captured_at=job.captured_at,
        observation_duration_seconds=settings.EMISSION_AGGREGATION_WINDOW_SECONDS,
        raw_detected_count=vehicle_counts, vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY,
    )
    with get_sync_db() as db:
        segment = db.execute(__import__("sqlalchemy").select(RoadSegment).where(RoadSegment.road_segment_id == mapping.road_segment_id)).scalar_one()
        db.add(SegmentTrafficObservationRecord(**observation_row(observation, road_segment_database_id=segment.id, camera_database_id=job.camera_database_id)))
        db.flush()
        metadata.update({"segment_pipeline_status": "observation_stored", "segment_id": mapping.road_segment_id})
        # Snapshot occupancy is retained for audit but is intentionally not scored as hourly volume.
        metadata["segment_pipeline_status"] = "pending_snapshot_semantics"
    return metadata


def publish_latest_state(camera_id: str, payload: dict) -> None:
    """Publish the compact latest aggregate state to WebSocket subscribers."""
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


def _aggregate_observation(
    job: InferenceJob,
    vehicle_counts: dict[str, int],
    *,
    queue_wait_s: float,
    inference_latency_s: float,
    cycle_duration_s: float,
) -> AggregationUpdate:
    return emission_aggregator.add(
        EmissionObservation(
            camera_id=job.camera_id,
            camera_database_id=job.camera_database_id,
            job_id=job.job_id,
            captured_at=job.captured_at,
            vehicle_counts=vehicle_counts,
            frame_acquisition_latency_s=job.frame_acquisition_latency_s,
            queue_wait_s=queue_wait_s,
            inference_latency_s=inference_latency_s,
            cycle_duration_s=cycle_duration_s,
        )
    )


def _record_aggregation(
    job: InferenceJob,
    vehicle_counts: dict[str, int],
    *,
    queue_wait_s: float,
    inference_latency_s: float,
    cycle_duration_s: float,
) -> dict:
    aggregation_started_at = time.monotonic()
    metadata = {
        "aggregation_status": "failed",
        "aggregation_window_seconds": settings.EMISSION_AGGREGATION_WINDOW_SECONDS,
    }
    try:
        update = _aggregate_observation(
            job,
            vehicle_counts,
            queue_wait_s=queue_wait_s,
            inference_latency_s=inference_latency_s,
            cycle_duration_s=cycle_duration_s,
        )
        aggregation_latency_s = time.monotonic() - aggregation_started_at
        metadata.update(
            {
                "aggregation_status": "collecting",
                "aggregation_period_start": update.current.period_start.isoformat(),
                "aggregation_period_end": update.current.period_end.isoformat(),
                "aggregation_sample_count": update.current.sample_count,
                "aggregation_latency_s": round(aggregation_latency_s, 6),
            }
        )
        try:
            latest_state = latest_state_store.save(update.current)
            metadata["latest_state_status"] = "stored"
            if not isinstance(latest_state, dict):
                raise TypeError("latest state store returned a non-object payload")
            try:
                publish_latest_state(job.camera_id, latest_state)
                metadata["realtime_status"] = "published"
            except Exception:
                metadata["realtime_status"] = "failed"
                logger.exception(
                    "latest_emission_realtime_publish_failed",
                    extra={"camera_id": job.camera_id, "job_id": job.job_id},
                )
        except Exception:
            metadata["latest_state_status"] = "failed"
            logger.exception(
                "latest_emission_state_store_failed",
                extra={"camera_id": job.camera_id, "job_id": job.job_id},
            )
        if update.completed:
            persistence_started_at = time.monotonic()
            try:
                persisted = historical_emission_store.save_many(update.completed)
                metadata.update(
                    {
                        "historical_persistence_status": "stored",
                        "historical_aggregates_persisted": persisted,
                        "historical_persistence_latency_s": round(
                            time.monotonic() - persistence_started_at,
                            6,
                        ),
                    }
                )
            except Exception:
                metadata["historical_persistence_status"] = "failed"
                metadata["historical_aggregates_persisted"] = 0
                logger.exception(
                    "historical_emission_aggregate_store_failed",
                    extra={"camera_id": job.camera_id, "job_id": job.job_id},
                )
        else:
            metadata.update(
                {
                    "historical_persistence_status": "not_due",
                    "historical_aggregates_persisted": 0,
                }
            )
        for completed in update.completed:
            logger.info(
                "emission_aggregation_window_completed",
                extra={
                    "camera_id": completed.camera_id,
                    "period_start": completed.period_start.isoformat(),
                    "period_end": completed.period_end.isoformat(),
                    "sample_count": completed.sample_count,
                    "aggregation_latency_s": round(aggregation_latency_s, 6),
                },
            )
    except Exception:
        logger.exception(
            "emission_aggregation_failed",
            extra={"camera_id": job.camera_id, "job_id": job.job_id},
        )
    return metadata


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
    """Decode one queued frame, run inference, aggregate, and publish latest state."""

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
        batch_outcome = inference_batcher.submit(
            frame,
            timeout_s=settings.INFERENCE_BATCH_RESULT_TIMEOUT_SECONDS,
        )
        vehicle_counts, _ = batch_outcome.result
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
    aggregation_metadata = _record_aggregation(
        job,
        vehicle_counts,
        queue_wait_s=queue_wait_s,
        inference_latency_s=inference_latency_s,
        cycle_duration_s=cycle_duration_s,
    )
    try:
        aggregation_metadata.update(_persist_segment_observation(job, vehicle_counts))
    except Exception:
        aggregation_metadata["segment_pipeline_status"] = "failed"
        logger.exception("segment_observation_persistence_failed", extra={"camera_id": job.camera_id, "job_id": job.job_id})

    processed_at = datetime.now(timezone.utc)
    result = {
        "camera_id": job.camera_id,
        "timestamp": processed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "captured_at": job.captured_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frame_acquisition_latency_s": round(job.frame_acquisition_latency_s, 3),
        "queue_wait_s": round(queue_wait_s, 3),
        "inference_latency_s": round(inference_latency_s, 3),
        "batch_wait_s": round(batch_outcome.batch_wait_s, 3),
        "batch_inference_latency_s": round(
            batch_outcome.batch_inference_latency_s,
            3,
        ),
        "batch_size": batch_outcome.batch_size,
        "job_id": job.job_id,
        "car": vehicle_counts["car"],
        "motorcycle": vehicle_counts["motorcycle"],
        "bus": vehicle_counts["bus"],
        "truck": vehicle_counts["truck"],
        "total_tsp_g_per_min": emission["total_tsp_g_per_min"],
        "total_tsp_kg_per_hr": emission["total_tsp_kg_per_hr"],
        "total_nox_g_per_min": emission["total_nox_g_per_min"],
        "total_nox_kg_per_hr": emission["total_nox_kg_per_hr"],
        "total_so2_g_per_min": emission["total_so2_g_per_min"],
        "total_so2_kg_per_hr": emission["total_so2_kg_per_hr"],
        "total_hc_g_per_min": emission["total_hc_g_per_min"],
        "total_hc_kg_per_hr": emission["total_hc_kg_per_hr"],
        "total_co_g_per_min": emission["total_co_g_per_min"],
        "total_co_kg_per_hr": emission["total_co_kg_per_hr"],
        "total_co2_g_per_min": emission["total_co2_g_per_min"],
        "total_co2_kg_per_hr": emission["total_co2_kg_per_hr"],
        "total_ch4_g_per_min": emission["total_ch4_g_per_min"],
        "total_ch4_kg_per_hr": emission["total_ch4_kg_per_hr"],
        "total_n2o_g_per_min": emission["total_n2o_g_per_min"],
        "total_n2o_kg_per_hr": emission["total_n2o_kg_per_hr"],
        "cycle_duration_s": round(cycle_duration_s, 2),
        **aggregation_metadata,
    }

    _cleanup_job(job)

    logger.info(
        "inference_job_completed",
        extra={
            "camera_id": job.camera_id,
            "job_id": job.job_id,
            "captured_at": job.captured_at.isoformat(),
            "queue_wait_s": round(queue_wait_s, 3),
            "inference_latency_s": round(inference_latency_s, 3),
            "batch_wait_s": round(batch_outcome.batch_wait_s, 3),
            "batch_inference_latency_s": round(
                batch_outcome.batch_inference_latency_s,
                3,
            ),
            "batch_size": batch_outcome.batch_size,
            "aggregation_status": aggregation_metadata["aggregation_status"],
            "aggregation_sample_count": aggregation_metadata.get(
                "aggregation_sample_count",
                0,
            ),
            "aggregation_latency_s": aggregation_metadata.get(
                "aggregation_latency_s",
                -1,
            ),
            "queue_depth": _queue_depth_or_unknown(),
        },
    )
    return result
