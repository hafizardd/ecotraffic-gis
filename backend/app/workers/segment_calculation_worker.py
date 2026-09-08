"""Periodic recalculation of emissions for mapped road segments."""

from collections import Counter
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
from app.services.segment_aggregation import SegmentAggregationError
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_emission_store import persist_segment_emission_sync
from app.services.segment_latest_state import SegmentLatestStateStore
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.services.spatial_integration import compute_all_spatial_criteria
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


def _pick_observations(records, segment_id: str):
    """Group by (duration, semantics); use largest group to survive mixed windows."""
    groups: dict[tuple, list] = {}
    for record in records:
        key = (record.observation_duration_seconds, record.vehicle_count_semantics)
        groups.setdefault(key, []).append(record)
    if len(groups) == 1:
        return [_record_to_observation(r, segment_id) for r in records], None
    largest = max(groups.values(), key=len)
    logger.warning("segment_mixed_observation_groups", extra={
        "segment_id": segment_id,
        "groups": {str(k): len(v) for k, v in groups.items()},
    })
    return [_record_to_observation(r, segment_id) for r in largest], f"mixed_groups:{len(groups)}"


@celery_app.task(name="app.workers.segment_calculation_worker.recalculate_segment_emissions")
def recalculate_segment_emissions() -> dict:
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(seconds=settings.SEGMENT_OBSERVATION_WINDOW_SECONDS)
    logger.info("segment_recalculation_window", extra={
        "aggregation_window_s": settings.EMISSION_AGGREGATION_WINDOW_SECONDS,
        "observation_window_s": settings.SEGMENT_OBSERVATION_WINDOW_SECONDS,
        "period": [period_start.isoformat(), now.isoformat()],
    })
    calculated = skipped = 0
    reasons: Counter = Counter()
    store = SegmentLatestStateStore(redis_client, settings.SEGMENT_LATEST_STATE_TTL_SECONDS)
    with get_sync_db() as db:
        segments = db.execute(select(RoadSegment).where(RoadSegment.id.in_(
            select(CameraRoadSegment.road_segment_id).where(CameraRoadSegment.is_active.is_(True))
        ))).scalars().all()
        for segment in segments:
            try:
                spatial = compute_all_spatial_criteria(db, segment)
            except Exception:
                logger.exception("segment_spatial_context_failed", extra={"segment_id": segment.road_segment_id})
                db.rollback()
                skipped += 1
                reasons["spatial_failed"] += 1
                continue
            segment.spatial_metadata = {**(segment.spatial_metadata or {}), "raw_values": spatial["raw_values"], "population_context": spatial["population_context"], "spatial_criteria_details": spatial["spatial_criteria_details"], "component_status": spatial["component_status"], "provenance": spatial["provenance"]}
            primary = (spatial["population_context"] or {}).get("primary")
            segment.population = primary.get("population") if primary else None
            records = db.execute(select(SegmentTrafficObservationRecord).where(
                SegmentTrafficObservationRecord.road_segment_id == segment.id,
                SegmentTrafficObservationRecord.captured_at >= period_start,
                SegmentTrafficObservationRecord.captured_at < now,
            )).scalars().all()
            if not records:
                db.commit()
                skipped += 1
                reasons["no_records"] += 1
                continue
            observations, group_note = _pick_observations(records, segment.road_segment_id)
            try:
                raw_values = spatial["raw_values"]
                result = calculate_segment_emission(
                    observations,
                    period_start=period_start, period_end=now, road_length_km=segment.length_km,
                    spatial_criteria={"K3": raw_values["K3"], "K4": raw_values["K4"], "K5": raw_values["K5"]},
                    spatial_details=spatial,
                )
                emission = persist_segment_emission_sync(db, segment.id, result)
                population_context = spatial["population_context"] or {}
                state = store.save(segment.road_segment_id, {
                    "decision_score": emission.decision_score, "priority": emission.priority,
                    "total_emission_g_h": sum(emission.pollutant_totals_g_h.values()),
                    "volume_per_hour": emission.volume_per_hour, "pollutant_totals": emission.pollutant_totals_g_h,
                    "calculated_at": emission.calculated_at.isoformat(), "spatial_criteria_status": emission.spatial_criteria_status,
                    "observed_at": emission.period_end.isoformat(),
                    "freshness_status": "fresh",
                    "vehicle_count_semantics": emission.vehicle_count_semantics,
                    "volume_status": "estimated" if emission.vehicle_count_semantics == "snapshot_occupancy" else "calculated",
                    "population": population_context.get("primary", {}).get("population"),
                    "population_district": population_context.get("primary", {}).get("district_name"),
                    "population_context": population_context,
                })
                db.commit()
                redis_client.publish(f"emissions:segment:{segment.road_segment_id}", json.dumps({"type": "segment_update", "segment_id": segment.road_segment_id, "data": state}))
                calculated += 1
                if group_note:
                    reasons[group_note] += 1
            except SegmentAggregationError as exc:
                # Spatial metadata is still valuable — commit it, skip only emission.
                logger.warning("segment_aggregation_skipped", extra={"segment_id": segment.road_segment_id, "error": str(exc)})
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                skipped += 1
                reasons[f"aggregation_error:{exc}"] += 1
            except Exception:
                logger.exception("segment_emission_calculation_failed", extra={"segment_id": segment.road_segment_id})
                db.rollback()
                skipped += 1
                reasons["calculation_failed"] += 1
    return {"calculated": calculated, "skipped": skipped, "reasons": dict(reasons)}
