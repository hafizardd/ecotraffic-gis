from app.workers.celery_app import celery_app

from app.core.database import get_sync_db
from app.models.camera import Camera
from app.models.emission import Emission
from sqlalchemy import select

from cv.detector import VehicleDetector
from cv.emission_factors import calculate_emission

import uuid
import time
from datetime import datetime, timezone
from app.core.config import settings

import redis
import json
import logging

logger = logging.getLogger(__name__)

_detector = None

def get_detector() -> VehicleDetector:
    global _detector
    if _detector is None:
        _detector = VehicleDetector()
    return _detector

def publish_to_redis(camera_id: str, payload: dict) -> None:
    r = redis.Redis.from_url(settings.REDIS_URL)
    channel = f"emissions:{camera_id}"
    r.publish(channel, json.dumps(payload))

@celery_app.task(bind=True, max_retries=3)
def process_camera(self, camera_id:str) -> dict:
    """
        Step 1: Load camera from DB
        Step 2: Capture frame call
        Step 3: Run detection
        Step 4: Calculate emission
        Step 5: Build result dict
        Step 6: Write to DB (new Emission row)
        Step 7: Publish to Redis channel for real-time updates
        Step 8: Return result (for logging)
    """
    start_time = time.time()

    with get_sync_db() as db:
        camera = db.execute(
            select(Camera).where(Camera.camera_id == camera_id)
        ).scalars().first()

        if camera is None or not camera.is_active:
            logger.warning(f"Camera with ID '{camera_id}' not found or is inactive.")
            return
        
        camera_uuid = camera.id
        stream_url = camera.stream_url
        referer = camera.referer
        camera_slug = camera.camera_id
    
    detector = get_detector()

    try:
        frame = detector.capture_frame(stream_url, referer)
    except RuntimeError as exc:
        logger.error(f"Failed to capture frame for camera '{camera_id}': {str(exc)}")
        self.retry(exc=exc, countdown=15)
        return
    
    vehicle_counts, _ = detector.detect(frame)

    emission = calculate_emission(vehicle_counts)

    cycle_duration = time.time() - start_time

    result = {
        "camera_id": camera_id,
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
        "cycle_duration_s": round(cycle_duration, 2)
    }
        
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

    publish_to_redis(camera_slug, result)

    return result