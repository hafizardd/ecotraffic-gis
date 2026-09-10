"""Reconcile closed, epoch-aligned segment windows from durable observations."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging

import redis
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import get_sync_db
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from app.services.emission_analytics import serialize_model
from app.services.segment_aggregation import select_one_camera_per_stream
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_emission_store import persist_segment_emission_sync
from app.services.segment_latest_state import SegmentLatestStateStore
from app.services.segment_observation import SegmentTrafficObservation, VehicleCountSemantics
from app.services.spatial_integration import compute_all_spatial_criteria
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
redis_client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def _record_to_observation(record, segment_id):
    return SegmentTrafficObservation(record.camera_identifier, segment_id, record.lane_or_stream_id,
        record.captured_at, record.observation_duration_seconds, record.raw_detected_count,
        VehicleCountSemantics(record.vehicle_count_semantics))


def _pick_observations(records, segment_id):
    priority = {"interval_count": 0, "vehicles_per_hour": 1, "snapshot_occupancy": 2}
    semantics = min((r.vehicle_count_semantics for r in records), key=lambda s: priority[s])
    chosen = [r for r in records if r.vehicle_count_semantics == semantics]
    note = "mixed_semantics_flow_preferred" if len(chosen) != len(records) else None
    return [_record_to_observation(r, segment_id) for r in chosen], note


def _window_start(moment, seconds):
    return datetime.fromtimestamp(int(moment.timestamp() // seconds) * seconds, timezone.utc)


def _reconciliation_start(earliest, last_start, next_observation, seconds):
    start = max(earliest, last_start - timedelta(seconds=12 * seconds)) if last_start else earliest
    # A long camera outage must not strand the cursor in an empty 120-window
    # batch forever. Jump to the next durable observation when necessary.
    if next_observation and next_observation >= start + timedelta(seconds=120 * seconds):
        start = next_observation - timedelta(seconds=12 * seconds)
    return _window_start(start, seconds)


def _publish(segment, emission, store):
    payload = serialize_model(segment, emission)
    payload.update(decision_score=emission.decision_score, priority=emission.priority,
        total_emission_g_h=sum((emission.pollutant_totals_g_h or {}).values()),
        total_emission_basis="sum_of_eight_pollutant_mass_rates_g_h",
        pollutant_totals=emission.pollutant_totals_g_h, calculated_at=emission.calculated_at.isoformat(),
        spatial_criteria_status=emission.spatial_criteria_status,
        volume_status="estimated" if emission.vehicle_count_semantics == "snapshot_occupancy" else "calculated")
    population = (segment.spatial_metadata or {}).get("population_context") or {}
    primary = population.get("primary") or {}
    payload.update(population_context=population, population=primary.get("population"), population_district=primary.get("district_name"))
    try:
        state = store.save(segment.road_segment_id, payload)
        redis_client.publish(f"emissions:segment:{segment.road_segment_id}",
            json.dumps({**state, "type": "segment_update", "data": state}))
    except Exception:
        logger.warning("segment_realtime_unavailable_fact_committed", extra={"segment_id": segment.road_segment_id}, exc_info=True)


@celery_app.task(name="app.workers.segment_calculation_worker.recalculate_segment_emissions")
def recalculate_segment_emissions():
    seconds = settings.SEGMENT_OBSERVATION_WINDOW_SECONDS
    closed_end = _window_start(datetime.now(timezone.utc), seconds)
    calculated = skipped = 0
    reasons = Counter()
    store = SegmentLatestStateStore(redis_client, settings.SEGMENT_LATEST_STATE_TTL_SECONDS)
    with get_sync_db() as db:
        segments = db.execute(select(RoadSegment).where(RoadSegment.id.in_(
            select(CameraRoadSegment.road_segment_id).where(CameraRoadSegment.is_active.is_(True))
        ))).scalars().all()
        for segment in segments:
            try:
                last_start = db.execute(select(func.max(SegmentEmission.period_start)).where(
                    SegmentEmission.road_segment_id == segment.id, SegmentEmission.calculation_version == 2,
                    SegmentEmission.ahp_metadata["source_mode"].astext == "LIVE")).scalar_one()
                earliest = db.execute(select(func.min(SegmentTrafficObservationRecord.captured_at)).where(
                    SegmentTrafficObservationRecord.road_segment_id == segment.id)).scalar_one()
                if earliest is None:
                    reasons["no_records"] += 1
                    continue
                # Replay recent windows for late inserts; catch up in bounded
                # batches after worker outages, using the durable last fact.
                next_observation = None
                if last_start:
                    next_observation = db.execute(select(func.min(SegmentTrafficObservationRecord.captured_at)).where(
                        SegmentTrafficObservationRecord.road_segment_id == segment.id,
                        SegmentTrafficObservationRecord.captured_at >= last_start + timedelta(seconds=seconds))).scalar_one()
                start = _reconciliation_start(earliest, last_start, next_observation, seconds)
                end = min(closed_end, start + timedelta(seconds=120 * seconds))
                if start >= end:
                    continue
                records = db.execute(select(SegmentTrafficObservationRecord).where(
                    SegmentTrafficObservationRecord.road_segment_id == segment.id,
                    SegmentTrafficObservationRecord.captured_at >= start,
                    SegmentTrafficObservationRecord.captured_at < end)).scalars().all()
                windows = defaultdict(list)
                for record in records:
                    windows[_window_start(record.captured_at, seconds)].append(record)
                existing = {e.period_start: e for e in db.execute(select(SegmentEmission).where(
                    SegmentEmission.road_segment_id == segment.id, SegmentEmission.period_start >= start,
                    SegmentEmission.period_start < end, SegmentEmission.calculation_version == 2)).scalars().all()}
                spatial = None
                for period_start, window in sorted(windows.items()):
                    observations, note = _pick_observations(window, segment.road_segment_id)
                    observations, dropped = select_one_camera_per_stream(observations)
                    if dropped:
                        logger.info("segment_duplicate_stream_deduped", extra={
                            "segment_id": segment.road_segment_id,
                            "dropped_cameras": dropped,
                            "kept_cameras": sorted({o.camera_id for o in observations}),
                        })
                    signature = hashlib.sha256(json.dumps(sorted((o.to_payload() for o in observations),
                        key=lambda o: (o["camera_id"], o["captured_at"])), sort_keys=True).encode()).hexdigest()
                    previous = existing.get(period_start)
                    if previous and (previous.ahp_metadata or {}).get("calculation_metadata", {}).get("observation_signature") == signature:
                        continue
                    if spatial is None:
                        spatial = compute_all_spatial_criteria(db, segment)
                        segment.spatial_metadata = {**(segment.spatial_metadata or {}), **spatial}
                        primary = (spatial.get("population_context") or {}).get("primary") or {}
                        segment.population = primary.get("population")
                    result = calculate_segment_emission(observations, period_start=period_start,
                        period_end=period_start + timedelta(seconds=seconds), road_length_km=segment.length_km,
                        spatial_criteria=spatial["raw_values"], spatial_details=spatial)
                    result["calculation_metadata"].update(observation_signature=signature, selection_note=note)
                    if dropped:
                        result["calculation_metadata"]["selection_note"] = "duplicate_stream_camera_deduped"
                        result["calculation_metadata"]["dropped_cameras"] = dropped
                    emission = persist_segment_emission_sync(db, segment.id, result)
                    db.commit()
                    calculated += 1
                    logger.info("segment_flow_calculated", extra={"segment_id": segment.road_segment_id,
                        "period_start": period_start.isoformat(), "vehicle_count_semantics": result["vehicle_count_semantics"],
                        "flow_count": result["raw_counts"], "volume_per_hour": result["volume_per_hour"],
                        "vkt_km_h": result["vkt_km_h"], "calculation_mode": result["calculation_mode"], "calculation_version": 2})
                    if note:
                        reasons[note] += 1
                # Retry Redis on every tick, including ticks without new facts.
                latest = db.execute(select(SegmentEmission).where(SegmentEmission.road_segment_id == segment.id,
                    SegmentEmission.ahp_metadata["source_mode"].astext == "LIVE")
                    .order_by(SegmentEmission.period_end.desc(), SegmentEmission.calculation_version.desc()).limit(1)).scalar_one_or_none()
                if latest:
                    _publish(segment, latest, store)
            except Exception:
                logger.exception("segment_emission_calculation_failed", extra={"segment_id": segment.road_segment_id})
                db.rollback()
                skipped += 1
                reasons["calculation_failed"] += 1
    return {"calculated": calculated, "skipped": skipped, "reasons": dict(reasons)}
