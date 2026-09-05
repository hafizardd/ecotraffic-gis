"""Periodic recalculation of emissions for mapped road segments."""

from datetime import datetime, timedelta, timezone
import json
import logging

import redis

from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_emission_store import persist_segment_emission_sync
from app.services.segment_latest_state import SegmentLatestStateStore
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
redis_client = redis.Redis.from_url(settings.REDIS_URL)


def _record_to_observation(record, segment_id: str) -> SegmentTrafficObservation:
    return SegmentTrafficObservation(
        camera_id=record.camera_identifier,
        road_segment_id=segment_id,
        lane_or_stream_id=record.lane_or_stream_id,
        captured_at=record.captured_at,
        observation_duration_seconds=record.observation_duration_seconds,
        raw_detected_count=record.raw_detected_count,
        vehicle_count_semantics=VehicleCountSemantics(record.vehicle_count_semantics),
    )


@celery_app.task(name="app.workers.segment_calculation_worker.recalculate_segment_emissions")
def recalculate_segment_emissions() -> dict:
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(seconds=settings.SEGMENT_OBSERVATION_WINDOW_SECONDS)
    calculated = skipped = 0
    store = SegmentLatestStateStore(redis_client, settings.SEGMENT_LATEST_STATE_TTL_SECONDS)
    with get_sync_db() as db:
        segments = db.execute(select(RoadSegment).where(RoadSegment.id.in_(
            select(CameraRoadSegment.road_segment_id).where(CameraRoadSegment.is_active.is_(True))
        ))).scalars().all()
        for segment in segments:
            records = db.execute(select(SegmentTrafficObservationRecord).where(
                SegmentTrafficObservationRecord.road_segment_id == segment.id,
                SegmentTrafficObservationRecord.captured_at >= period_start,
                SegmentTrafficObservationRecord.captured_at < now,
            )).scalars().all()
            if not records:
                skipped += 1
                continue
            try:
                result = calculate_segment_emission(
                    [_record_to_observation(record, segment.road_segment_id) for record in records],
                    period_start=period_start, period_end=now, road_length_km=segment.length_km,
                    spatial_criteria={"K3": settings.DEFAULT_SPATIAL_CRITERIA_K3, "K4": settings.DEFAULT_SPATIAL_CRITERIA_K4, "K5": settings.DEFAULT_SPATIAL_CRITERIA_K5},
                )
                emission = persist_segment_emission_sync(db, segment.id, result)
                state = store.save(segment.road_segment_id, {
                    "decision_score": emission.decision_score, "priority": emission.priority,
                    "total_emission_g_h": sum(emission.pollutant_totals_g_h.values()),
                    "volume_per_hour": emission.volume_per_hour, "pollutant_totals": emission.pollutant_totals_g_h,
                    "calculated_at": emission.calculated_at.isoformat(), "spatial_criteria_status": emission.spatial_criteria_status,
                })
                redis_client.publish(f"emissions:segment:{segment.road_segment_id}", json.dumps({"type": "segment_update", "segment_id": segment.road_segment_id, "data": state}))
                calculated += 1
            except Exception:
                logger.exception("segment_emission_calculation_failed", extra={"segment_id": segment.road_segment_id})
    return {"calculated": calculated, "skipped": skipped}
