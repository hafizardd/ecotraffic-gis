"""Continuous ByteTrack worker for ROI verification (2 LIVE cameras only).

Runs outside the snapshot inference path: one thread per camera holds its own
YOLO tracker state (persist=True) so IDs survive across frames. Publishes
lightweight track payloads on ``tracks:{camera_id}`` (Redis/analytics) and
stores the latest annotated JPEG (filled ROI + dimmed outside boxes) under
``tracks:snapshot:{camera_id}`` — the single source for the browser MJPEG
display stream at ``GET /api/cameras/{id}/tracked.mjpg``.

Run: ``python -m app.workers.tracking_worker`` (separate process/container).
Snapshot emissions path is untouched.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

import redis

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from app.services.camera_management import get_active_camera_source
from app.services.emission_aggregation import EmissionObservation, EmissionWindowAggregator
from app.services.historical_emission_store import HistoricalEmissionStore
from app.services.latest_emission_state import LatestEmissionStateStore
from app.services.segment_mapping import CameraSegmentMapping, MappingResolutionError, resolve_camera_mapping
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.services.segment_observation_store import observation_row
from cv.detector import VehicleDetector
from cv.frame_store import RedisFrameStore
from cv.rois import to_normalized
from cv.emission_factors import calculate_emission
from cv.track_emission import FlowCounter, occupancy_counts

logger = logging.getLogger(__name__)

TRACK_CHANNEL_PREFIX = "tracks:"
SNAPSHOT_KEY_PREFIX = "tracks:snapshot:"


def _track_cams() -> list[str]:
    return [c.strip() for c in settings.TRACK_CAMS.split(",") if c.strip()]


_segment_mappings_cache: tuple[float, list[CameraSegmentMapping]] | None = None


def _load_segment_mappings_cached() -> list[CameraSegmentMapping]:
    """Sync mapping cache for tracking threads (standalone loader)."""
    global _segment_mappings_cache
    now = time.monotonic()
    if _segment_mappings_cache is not None and now - _segment_mappings_cache[0] < settings.SEGMENT_MAPPING_CACHE_TTL_SECONDS:
        return _segment_mappings_cache[1]
    from sqlalchemy import select

    from app.models.camera import Camera

    with get_sync_db() as db:
        rows = db.execute(
            select(
                Camera.camera_id,
                RoadSegment.road_segment_id, CameraRoadSegment.lane_or_stream_id,
                CameraRoadSegment.is_active, CameraRoadSegment.valid_from, CameraRoadSegment.valid_to,
            ).join(CameraRoadSegment, CameraRoadSegment.camera_id == Camera.id)
            .join(RoadSegment, CameraRoadSegment.road_segment_id == RoadSegment.id)
            .where(CameraRoadSegment.is_active.is_(True))
        ).all()
    _segment_mappings_cache = (now, [CameraSegmentMapping(*row) for row in rows])
    return _segment_mappings_cache[1]


def _persist_segment_snapshot(camera_id: str, camera_database_id: str, occupancy: dict, captured_at: datetime) -> str:
    """Write one snapshot_occupancy observation so the segment worker can score tracked cameras.

    Returns a segment_pipeline_status string; never raises (loop must survive).
    """
    from sqlalchemy import select

    try:
        mapping = resolve_camera_mapping(_load_segment_mappings_cached(), camera_id=camera_id, captured_at=captured_at)
    except MappingResolutionError:
        logger.warning("tracking_segment_no_mapping", extra={"camera_id": camera_id})
        return "no_mapping"
    observation = SegmentTrafficObservation(
        camera_id=camera_id, road_segment_id=mapping.road_segment_id,
        lane_or_stream_id=mapping.lane_or_stream_id, captured_at=captured_at,
        observation_duration_seconds=settings.EMISSION_AGGREGATION_WINDOW_SECONDS,
        raw_detected_count=dict(occupancy), vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY,
    )
    try:
        with get_sync_db() as db:
            segment = db.execute(select(RoadSegment).where(RoadSegment.road_segment_id == mapping.road_segment_id)).scalar_one()
            db.add(SegmentTrafficObservationRecord(**observation_row(observation, road_segment_database_id=segment.id, camera_database_id=camera_database_id)))
            db.flush()
    except Exception:
        logger.exception("tracking_segment_observation_persistence_failed", extra={"camera_id": camera_id})
        return "failed"
    return "observation_stored"


def _build_tracker(camera_id: str) -> VehicleDetector:
    return VehicleDetector(
        model_path=settings.YOLO_MODEL_PATH,
        confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        device=settings.YOLO_DEVICE,
        image_size=settings.YOLO_IMAGE_SIZE,
        camera_id=camera_id,
    )


def _track_options(detector: VehicleDetector) -> dict:
    options = detector._inference_options()
    options.update({"persist": True, "tracker": settings.YOLO_TRACKER, "iou": settings.YOLO_IOU})
    return options


def _parse_tracks(detector: VehicleDetector, frame, result) -> list[dict]:
    h, w = frame.shape[:2]
    roi_poly = detector._roi_polygon(frame)
    tracks = []
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return tracks
    for box in boxes:
        try:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
        except (TypeError, IndexError, ValueError):
            continue
        if cls_id not in detector.vehicle_classes or conf < detector.confidence_threshold:
            continue
        x1, y1, x2, y2 = map(float, box.xyxy[0])
        inside = (
            detector._box_center_inside(roi_poly, int(x1), int(y1), int(x2), int(y2))
            if roi_poly is not None
            else True
        )
        tracks.append(
            {
                "id": VehicleDetector._box_track_id(box),
                "cls": detector.vehicle_classes[cls_id],
                "conf": round(conf, 3),
                "x1": round(x1 / w, 4),
                "y1": round(y1 / h, 4),
                "x2": round(x2 / w, 4),
                "y2": round(y2 / h, 4),
                "inside_roi": inside,
            }
        )
    return tracks


def _open_capture(cv2_module, stream_url: str, referer: str | None):
    """Open a capture with Referer + timeouts (Wowza requires Referer)."""
    env_key = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    previous = os.environ.get(env_key)
    try:
        if referer:
            os.environ[env_key] = f"headers=Referer: {referer}\r\n"
        cap = cv2_module.VideoCapture()
        open_ms = int(float(settings.FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS) * 1000)
        read_ms = int(float(settings.FRAME_CAPTURE_READ_TIMEOUT_SECONDS) * 1000)
        for prop, value in (
            ("CAP_PROP_OPEN_TIMEOUT_MSEC", open_ms),
            ("CAP_PROP_READ_TIMEOUT_MSEC", read_ms),
        ):
            prop_id = getattr(cv2_module, prop, None)
            if prop_id is not None:
                try:
                    cap.set(prop_id, value)
                except Exception:
                    pass
        backend = getattr(cv2_module, "CAP_FFMPEG", 0)
        buffer_prop = getattr(cv2_module, "CAP_PROP_BUFFERSIZE", None)
        if buffer_prop is not None:
            try:
                cap.set(buffer_prop, 1)
            except Exception:
                pass
        if not cap.open(stream_url, backend) or not cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
            return None
        return cap
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous


def run_camera_loop(camera_id: str, stop: threading.Event) -> None:
    import cv2

    camera = get_active_camera_source(camera_id)
    if camera is None:
        logger.warning("tracking_camera_missing", extra={"camera_id": camera_id})
        return
    detector = _build_tracker(camera_id)
    options = _track_options(detector)
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    latest_state_store = LatestEmissionStateStore(
        redis_client,
        ttl_seconds=settings.LATEST_EMISSION_STATE_TTL_SECONDS,
    )
    aggregator = EmissionWindowAggregator(
        window_seconds=settings.TRACK_DB_FLUSH_SECONDS,
    )
    flow = FlowCounter(
        min_frames=settings.TRACK_FLOW_MIN_FRAMES,
        exit_frames=settings.TRACK_FLOW_EXIT_FRAMES,
    )
    historical_store = HistoricalEmissionStore()
    snapshots = RedisFrameStore(
        redis_client,
        ttl_seconds=settings.TRACK_SNAPSHOT_TTL_SECONDS,
        max_bytes=settings.INFERENCE_FRAME_MAX_BYTES,
        jpeg_quality=settings.STREAM_JPEG_QUALITY,
        key_prefix=SNAPSHOT_KEY_PREFIX,
    )
    interval = 1.0 / float(settings.TRACK_FPS)
    next_deadline = time.monotonic()
    last_segment_persist = 0.0

    cap = _open_capture(cv2, camera.stream_url, camera.referer)
    if cap is None:
        logger.warning("tracking_open_failed", extra={"camera_id": camera_id})
    consecutive_misses = 0
    try:
        while not stop.is_set():
            if cap is None:
                # Reconnect with bounded exponential backoff.
                delay = min(30.0, 2.0 ** min(consecutive_misses, 5))
                time.sleep(delay)
                # Referer can rotate in DB; refresh without restarting the thread.
                fresh = get_active_camera_source(camera_id)
                url = fresh.stream_url if fresh else camera.stream_url
                ref = fresh.referer if fresh else camera.referer
                cap = _open_capture(cv2, url, ref)
                if cap is None:
                    consecutive_misses += 1
                    continue
                consecutive_misses = 0
                continue
            # Read the newest available frame instead of allowing a decoder
            # buffer to turn inference into a delayed replay.
            ok = cap.grab()
            if ok:
                ok, frame = cap.retrieve()
            else:
                frame = None
            if not ok or frame is None:
                consecutive_misses += 1
                logger.warning("tracking_frame_missed", extra={"camera_id": camera_id})
                if consecutive_misses >= 10:
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
                    continue
                time.sleep(min(interval, 0.1))
                continue
            consecutive_misses = 0
            try:
                # Ultralytics validates tracking-only arguments in model.track;
                # passing persist to model(...) raises on current releases.
                results = list(detector.model.track(frame, **options))
            except Exception:
                logger.exception("tracking_inference_failed", extra={"camera_id": camera_id})
                time.sleep(interval)
                continue
            if not results:
                time.sleep(interval)
                continue
            result = results[0]
            tracks = _parse_tracks(detector, frame, result)
            occupancy = occupancy_counts(tracks)
            flow_exits = flow.update(tracks)
            captured_at = datetime.now(timezone.utc)
            # One snapshot_occupancy row per observation window so the segment
            # worker (which reads [now-window, now)) always finds tracked cameras.
            if time.monotonic() - last_segment_persist >= settings.SEGMENT_OBSERVATION_WINDOW_SECONDS:
                _persist_segment_snapshot(camera_id, str(camera.id), occupancy, captured_at)
                last_segment_persist = time.monotonic()
            current = aggregator.add(
                EmissionObservation(
                    camera_id=camera_id,
                    camera_database_id=str(camera.id),
                    job_id=f"track-{camera_id}-{captured_at.timestamp()}",
                    captured_at=captured_at,
                    vehicle_counts=occupancy,
                )
            )
            instant_emission = calculate_emission(occupancy)
            latest = latest_state_store.payload_for(current.current)
            latest.update({
                "type": "emission_update",
                "source": "tracking",
                "occupancy": occupancy,
                "flow_exits": flow_exits,
                "instant_emission": instant_emission,
            })
            try:
                redis_client.setex(
                    latest_state_store.key_for(camera_id),
                    settings.LATEST_EMISSION_STATE_TTL_SECONDS,
                    json.dumps(latest, separators=(",", ":")),
                )
                redis_client.publish(f"emissions:{camera_id}", json.dumps(latest))
            except Exception:
                logger.exception("tracking_emission_publish_failed", extra={"camera_id": camera_id})
            for completed in current.completed:
                try:
                    historical_store.save_many((completed,))
                except Exception:
                    logger.exception("tracking_historical_emission_store_failed", extra={"camera_id": camera_id})
            # Annotated snapshot: filled ROI + dimmed outside boxes, IDs on labels.
            _, annotated = detector._parse_result(frame, result, annotate=True)
            try:
                snapshots.store(camera_id, annotated)
            except Exception:
                logger.warning("tracking_snapshot_store_failed", extra={"camera_id": camera_id})
            payload = {
                "type": "track_update",
                "camera_id": camera_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tracks": tracks,
                "occupancy": occupancy,
                "flow_exits": flow_exits,
                "instant_emission": instant_emission,
                "roi": to_normalized(camera_id),
            }
            try:
                redis_client.publish(f"{TRACK_CHANNEL_PREFIX}{camera_id}", json.dumps(payload))
            except Exception:
                logger.warning("tracking_publish_failed", extra={"camera_id": camera_id})
            next_deadline += interval
            delay = next_deadline - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_deadline = time.monotonic()
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def main() -> None:
    stop = threading.Event()
    threads = [
        threading.Thread(target=run_camera_loop, args=(cam, stop), daemon=True)
        for cam in _track_cams()
    ]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1.0)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
