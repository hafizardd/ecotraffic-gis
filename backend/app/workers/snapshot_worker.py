"""Batched one-frame YOLO snapshot sampler for HISTORICAL cameras.

Claim-lease scheduling on the existing ``cameras.next_sample_at`` column: each
cycle claims due non-LIVE cameras, grabs one frame per camera, runs one shared
batched YOLO inference per chunk, and stores a SNAPSHOT_OCCUPANCY observation.
Each observation is then scored immediately with ``calculate_segment_emission``
and persisted with ``source_mode = "SNAPSHOT_REAL"``.

The LIVE tracking path and the LIVE-only reconciler are untouched. Heavy CV
imports stay lazy so the backend/beat/segment-worker images (no PyTorch) can
still import this module to register the task.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import logging
import time

from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.road_segment import RoadSegment
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_aggregation import select_one_camera_per_stream
from app.services.segment_emission_store import persist_segment_emission_sync
from app.services.segment_mapping import CameraSegmentMapping, MappingResolutionError, resolve_camera_mapping
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.services.segment_observation_store import observation_row
from app.services.spatial_integration import compute_all_spatial_criteria
from app.workers.celery_app import celery_app
from app.workers.segment_calculation_worker import _window_start
from cv.rois import resolve as resolve_roi

logger = logging.getLogger(__name__)

_detector = None

_CLAIM_SQL = text("""
    WITH due AS (
        SELECT id FROM cameras
        WHERE data_source <> 'LIVE' AND is_active
          AND (next_sample_at IS NULL OR next_sample_at <= now())
        ORDER BY next_sample_at ASC NULLS FIRST
        LIMIT :limit
        FOR UPDATE SKIP LOCKED
    )
    UPDATE cameras c
    SET next_sample_at = now() + make_interval(secs => COALESCE(
            c.sampling_interval_seconds,
            CASE c.priority
                WHEN 'high' THEN :high
                WHEN 'low' THEN :low
                ELSE :medium
            END))
    FROM due
    WHERE c.id = due.id
    RETURNING c.id, c.camera_id, c.stream_url, c.referer,
              c.priority, c.sampling_interval_seconds
""")

_DUE_SQL = text("""
    SELECT id, camera_id, stream_url, referer, priority, sampling_interval_seconds
    FROM cameras
    WHERE data_source <> 'LIVE' AND is_active
      AND (next_sample_at IS NULL OR next_sample_at <= now())
    ORDER BY next_sample_at ASC NULLS FIRST
    LIMIT :limit
""")


def _get_detector():
    global _detector
    if _detector is None:
        from cv.detector import VehicleDetector

        _detector = VehicleDetector(
            model_path=settings.YOLO_MODEL_PATH,
            confidence_threshold=settings.CONFIDENCE_THRESHOLD,
            device=settings.YOLO_DEVICE,
            image_size=settings.YOLO_IMAGE_SIZE,
        )
    return _detector


def _effective_interval(priority: str | None, sampling_interval_seconds: int | None) -> int:
    if sampling_interval_seconds:
        return int(sampling_interval_seconds)
    return {
        "high": settings.SNAPSHOT_HIGH_INTERVAL_SECONDS,
        "medium": settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS,
        "low": settings.SNAPSHOT_LOW_INTERVAL_SECONDS,
    }.get(priority, settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS)


def _claim_due_cameras(db, limit: int):
    return db.execute(_CLAIM_SQL, {
        "limit": limit,
        "high": settings.SNAPSHOT_HIGH_INTERVAL_SECONDS,
        "medium": settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS,
        "low": settings.SNAPSHOT_LOW_INTERVAL_SECONDS,
    }).mappings().all()


def _due_cameras(db, limit: int):
    return db.execute(_DUE_SQL, {"limit": limit}).mappings().all()


def _load_active_mappings(db) -> list[CameraSegmentMapping]:
    from app.models.camera import Camera
    from app.models.camera_road_segment import CameraRoadSegment

    rows = db.execute(
        select(
            Camera.camera_id,
            RoadSegment.road_segment_id, CameraRoadSegment.lane_or_stream_id,
            CameraRoadSegment.is_active, CameraRoadSegment.valid_from, CameraRoadSegment.valid_to,
        ).join(CameraRoadSegment, CameraRoadSegment.camera_id == Camera.id)
        .join(RoadSegment, CameraRoadSegment.road_segment_id == RoadSegment.id)
        .where(CameraRoadSegment.is_active.is_(True))
    ).all()
    return [CameraSegmentMapping(*row) for row in rows]


def _mark_success(db, camera_db_id, when: datetime) -> None:
    db.execute(text(
        "UPDATE cameras SET last_sample_at = :when, last_success_at = :when, "
        "failure_count = 0, status = 'active' WHERE id = :id"
    ), {"when": when, "id": camera_db_id})


def _mark_failure(db, camera_db_id, when: datetime) -> None:
    db.execute(text(
        "UPDATE cameras SET last_sample_at = :when, last_error_at = :when, "
        "failure_count = failure_count + 1, "
        "status = CASE WHEN failure_count + 1 >= :threshold THEN 'offline' ELSE 'degraded' END "
        "WHERE id = :id"
    ), {"when": when, "id": camera_db_id, "threshold": settings.SNAPSHOT_FAILURES_BEFORE_OFFLINE})


def _chunks(items, size: int):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _run_dry_run(cameras) -> dict:
    """Grab + infer + log counts only; never writes to the database."""
    from cv.capture import grab_frame

    detector = _get_detector()
    stats = Counter()
    for camera in cameras:
        frame = grab_frame(camera["stream_url"], camera["referer"])
        if frame is None:
            stats["grab_failed"] += 1
            logger.info("snapshot_dry_run_grab_failed", extra={"camera_id": camera["camera_id"]})
            continue
        result = detector.infer_batch([frame])[0]
        counts = detector.parse_result_for_camera(frame, result, camera["camera_id"])
        logger.info("snapshot_dry_run_frame", extra={"camera_id": camera["camera_id"], "counts": counts})
        stats["ok"] += 1
    return dict(stats)


@celery_app.task(name="app.workers.snapshot_worker.sample_historical_cameras")
def sample_historical_cameras(dry_run: bool | None = None) -> dict:
    """One sampling cycle over due HISTORICAL cameras."""
    dry = settings.SNAPSHOT_DRY_RUN if dry_run is None else dry_run
    started = time.monotonic()
    stats = Counter()
    with get_sync_db() as db:
        cameras = _due_cameras(db, settings.SNAPSHOT_CLAIM_BATCH_SIZE) if dry else \
            _claim_due_cameras(db, settings.SNAPSHOT_CLAIM_BATCH_SIZE)
        db.commit()
        if not cameras:
            return {"claimed": 0, "cycle_seconds": round(time.monotonic() - started, 2)}
        if dry:
            stats.update(_run_dry_run(cameras))
            stats["claimed"] = len(cameras)
            stats["cycle_seconds"] = round(time.monotonic() - started, 2)
            logger.info("snapshot_cycle", extra=dict(stats))
            return dict(stats)

        from cv.capture import grab_frame

        detector = _get_detector()
        mappings = _load_active_mappings(db)
        collected: list[tuple[SegmentTrafficObservation, RoadSegment, bool]] = []
        stats["claimed"] = len(cameras)

        for chunk in _chunks(list(cameras), settings.SNAPSHOT_CHUNK_SIZE):
            pairs = []
            for camera in chunk:
                frame = grab_frame(camera["stream_url"], camera["referer"])
                if frame is None:
                    _mark_failure(db, camera["id"], datetime.now(timezone.utc))
                    stats["grab_failed"] += 1
                    continue
                pairs.append((camera, frame))
            db.commit()
            if not pairs:
                continue

            results = detector.infer_batch([frame for _, frame in pairs])
            for (camera, frame), result in zip(pairs, results):
                camera_id = camera["camera_id"]
                try:
                    counts = detector.parse_result_for_camera(frame, result, camera_id)
                    captured_at = datetime.now(timezone.utc)
                    mapping = resolve_camera_mapping(mappings, camera_id=camera_id, captured_at=captured_at)
                    segment = db.execute(
                        select(RoadSegment).where(RoadSegment.road_segment_id == mapping.road_segment_id)
                    ).scalar_one()
                    _mark_success(db, camera["id"], captured_at)
                    observation = SegmentTrafficObservation(
                        camera_id, mapping.road_segment_id, mapping.lane_or_stream_id,
                        captured_at,
                        _effective_interval(camera["priority"], camera["sampling_interval_seconds"]),
                        counts, vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY,
                    )
                    db.add(SegmentTrafficObservationRecord(**observation_row(
                        observation, road_segment_database_id=segment.id,
                        camera_database_id=camera["id"],
                    )))
                    db.commit()
                    collected.append((observation, segment, bool(resolve_roi(camera_id))))
                    stats["observations"] += 1
                except MappingResolutionError:
                    db.rollback()
                    stats["no_mapping"] += 1
                    logger.warning("snapshot_no_mapping", extra={"camera_id": camera_id})
                except Exception:
                    db.rollback()
                    stats["camera_failed"] += 1
                    logger.exception("snapshot_camera_failed", extra={"camera_id": camera_id})

        _calculate_emissions(db, collected, stats)
    stats["cycle_seconds"] = round(time.monotonic() - started, 2)
    logger.info("snapshot_cycle", extra=dict(stats))
    return dict(stats)


def _select_stream_observations(items):
    """Thin wrapper over the shared selector for ``(observation, segment, roi)``
    tuples. Returns ``(selected, dropped_by_stream)``."""
    selected, dropped = select_one_camera_per_stream([item[0] for item in items])
    kept = {id(observation) for observation in selected}
    return [item for item in items if id(item[0]) in kept], dropped


def _calculate_emissions(db, collected, stats: Counter) -> None:
    if not collected:
        return
    seconds = settings.SEGMENT_OBSERVATION_WINDOW_SECONDS
    groups: dict[tuple, list] = defaultdict(list)
    for observation, segment, has_roi in collected:
        groups[(str(segment.id), _window_start(observation.captured_at, seconds))].append(
            (observation, segment, has_roi)
        )

    spatial_cache: dict[str, dict] = {}
    for (_segment_db_id, period_start), items in groups.items():
        segment = items[0][1]
        items, dropped = _select_stream_observations(items)
        if dropped:
            logger.info("snapshot_duplicate_stream_deduped", extra={
                "segment_id": segment.road_segment_id,
                "dropped_cameras": dropped,
                "kept_cameras": sorted({observation.camera_id for observation, _, _ in items}),
            })
        try:
            spatial = spatial_cache.get(str(segment.id))
            if spatial is None:
                spatial = compute_all_spatial_criteria(db, segment)
                spatial_cache[str(segment.id)] = spatial
                segment.spatial_metadata = {
                    **(segment.spatial_metadata or {}),
                    "raw_values": spatial["raw_values"],
                    "population_context": spatial["population_context"],
                    "spatial_criteria_details": spatial["spatial_criteria_details"],
                    "component_status": spatial["component_status"],
                    "provenance": spatial["provenance"],
                }
                primary = (spatial["population_context"] or {}).get("primary")
                segment.population = primary.get("population") if primary else None
            result = calculate_segment_emission(
                [observation for observation, _, _ in items],
                period_start=period_start,
                period_end=period_start + timedelta(seconds=seconds),
                road_length_km=segment.length_km,
                spatial_criteria=spatial["raw_values"],
                spatial_details=spatial,
            )
            result["data_source"] = "HISTORICAL"
            result["source_mode"] = "SNAPSHOT_REAL"
            result["calculation_metadata"]["roi_status"] = (
                "calibrated" if all(has_roi for _, _, has_roi in items) else "uncalibrated"
            )
            if dropped:
                result["calculation_metadata"]["selection_note"] = "duplicate_stream_camera_deduped"
                result["calculation_metadata"]["dropped_cameras"] = dropped
            persist_segment_emission_sync(db, segment.id, result)
            db.commit()
            stats["emissions"] += 1
        except Exception:
            db.rollback()
            stats["emission_failed"] += 1
            logger.exception("snapshot_emission_failed", extra={"segment_id": segment.road_segment_id})
