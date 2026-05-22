from app.workers.celery_app import celery_app

from app.core.database import get_sync_db
from app.models.camera import Camera
from app.models.emission import Emission
from sqlalchemy import select

from cv.detector import VehicleDetector
from cv.emission_factors import calculate_emission

import threading
import uuid
import time
from datetime import datetime, timezone
from app.core.config import settings

import redis
import json
import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Thread-local detector singleton
# Each worker thread gets its own VehicleDetector instance — safe for
# --pool=threads concurrency. Loads model once per thread, not per task.
# ------------------------------------------------------------------

_thread_local = threading.local()


def get_detector() -> VehicleDetector:
    if not hasattr(_thread_local, 'detector'):
        logger.info("Loading YOLO model for thread...")
        _thread_local.detector = VehicleDetector()
    return _thread_local.detector


def publish_to_redis(camera_id: str, payload: dict) -> None:
    r = redis.Redis.from_url(settings.REDIS_URL)
    channel = f"emissions:{camera_id}"
    r.publish(channel, json.dumps(payload))
    r.close()


@celery_app.task(bind=True, max_retries=3)
def process_camera(self, camera_id: str) -> dict:
    """
    Step 1: Load camera from DB
    Step 2: Capture frame
    Step 3: Run detection
    Step 4: Calculate emission
    Step 5: Build result dict
    Step 6: Write to DB
    Step 7: Publish to Redis
    Step 8: Return result
    """
    start_time = time.time()

    # Step 1 — Load camera from DB
    with get_sync_db() as db:
        camera = db.execute(
            select(Camera).where(Camera.camera_id == camera_id)
        ).scalars().first()

        if camera is None or not camera.is_active:
            logger.warning(f"Camera '{camera_id}' not found or inactive.")
            return

        camera_uuid = camera.id
        stream_url = camera.stream_url
        referer = camera.referer
        camera_slug = camera.camera_id

    # Step 2 — Capture frame
    detector = get_detector()

    try:
        frame = detector.capture_frame(stream_url, referer)
    except RuntimeError as exc:
        logger.error(f"Frame capture failed for '{camera_id}': {exc}")
        raise self.retry(exc=exc, countdown=15)

    # Step 3 — Detect vehicles
    vehicle_counts, _ = detector.detect(frame)

    # Step 4 — Calculate emissions
    emission = calculate_emission(vehicle_counts)

    cycle_duration = time.time() - start_time

    # Step 5 — Build result dict
    result = {
        "camera_id": camera_slug,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        "cycle_duration_s": round(cycle_duration, 2),
    }

    # Step 6 — Write to DB
    with get_sync_db() as db:
        db.add(Emission(
            id=uuid.uuid4(),
            camera_id=camera_uuid,
            timestamp=datetime.now(timezone.utc),
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
            cycle_duration_s=round(cycle_duration, 2),
        ))

    # Step 7 — Publish to Redis
    publish_to_redis(camera_slug, result)

    return result