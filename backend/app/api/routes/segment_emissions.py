from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.models.camera_road_segment import CameraRoadSegment
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from app.schemas.segment_emission import SegmentEmissionMapItem, SegmentEmissionResponse
from app.core.config import settings
from app.services.data_freshness import FreshnessPolicy, classify_freshness

router = APIRouter(tags=["segment-emissions"])


@router.get("/api/segments/geojson")
async def get_segments_geojson(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoadSegment, SegmentEmission)
        .outerjoin(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .order_by(RoadSegment.road_segment_id, SegmentEmission.period_end.desc().nullslast())
    )
    latest = {}
    for segment, emission in result:
        latest.setdefault(segment.id, (segment, emission))
    features = []
    for segment, emission in latest.values():
        geometry = (await db.execute(
            select(text("ST_AsGeoJSON(road_segments.geometry)::json"))
            .where(RoadSegment.id == segment.id)
        )).scalar_one()
        properties = {"segment_id": segment.road_segment_id, "name": segment.name, "length_km": segment.length_km,
                      "decision_score": None, "priority": None, "pollutant_totals": None,
                      "volume_per_hour": None, "total_emission_g_h": None,
                      "freshness_status": "unknown", "data_age_seconds": None,
                      "vehicle_count_semantics": "unknown", "source_cameras": []}
        if emission:
            pollutant_totals = emission.pollutant_totals_g_h
            freshness = classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings))
            properties.update({"decision_score": emission.decision_score, "priority": emission.priority,
                               "pollutant_totals": pollutant_totals, "volume_per_hour": emission.volume_per_hour,
                               "total_emission_g_h": sum(pollutant_totals.values()) if pollutant_totals else None,
                               "freshness_status": freshness.status.value, "data_age_seconds": freshness.age_seconds,
                               "vehicle_count_semantics": emission.vehicle_count_semantics,
                               "source_cameras": emission.source_cameras})
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    return JSONResponse({"type": "FeatureCollection", "features": features})


@router.get("/api/emissions/map", response_model=list[SegmentEmissionMapItem])
async def get_segment_emission_map(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoadSegment, SegmentEmission)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .order_by(RoadSegment.road_segment_id, SegmentEmission.period_end.desc())
    )
    latest = {}
    for segment, emission in result:
        latest.setdefault(segment.road_segment_id, (segment, emission))
    return [
        SegmentEmissionMapItem(
            road_segment_id=segment.road_segment_id, decision_score=emission.decision_score,
            priority=emission.priority,
            total_emission=(sum(emission.pollutant_totals_g_h.values()) if emission.pollutant_totals_g_h else None),
             calculated_at=emission.calculated_at, observed_at=emission.period_end,
             data_age_seconds=classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings)).age_seconds,
             freshness_status=classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings)).status.value,
             vehicle_count_semantics=emission.vehicle_count_semantics,
             source_cameras=emission.source_cameras,
        )
        for segment, emission in latest.values()
    ]


@router.get("/api/emissions/{road_segment_id}", response_model=SegmentEmissionResponse)
async def get_segment_emission(road_segment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoadSegment, SegmentEmission)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(RoadSegment.road_segment_id == road_segment_id)
        .order_by(SegmentEmission.period_end.desc(), SegmentEmission.calculation_version.desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Road segment '{road_segment_id}' has no emission result")
    segment, emission = row
    return SegmentEmissionResponse(
        road_segment_id=segment.road_segment_id, name=segment.name, length_km=segment.length_km,
        period_start=emission.period_start, period_end=emission.period_end, calculated_at=emission.calculated_at,
        raw_counts=emission.raw_counts, volume_per_hour=emission.volume_per_hour, vkt_km_h=emission.vkt_km_h,
        pollutant_totals_g_h=emission.pollutant_totals_g_h, category_pollutant_breakdown_g_h=emission.category_pollutant_breakdown_g_h,
        raw_criteria=emission.raw_criteria, normalized_criteria=emission.normalized_criteria,
        decision_score=emission.decision_score, priority=emission.priority, spatial_criteria_status=emission.spatial_criteria_status,
        provenance={"source_cameras": emission.source_cameras, "source_streams": emission.source_streams, "aggregation_policy": emission.aggregation_policy},
        ahp_metadata=emission.ahp_metadata,
        volume_status="unavailable" if emission.volume_per_hour is None else "calculated",
        vehicle_count_semantics=emission.vehicle_count_semantics,
        freshness_status=classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings)).status.value,
    )


@router.get("/api/segments/diagnostics")
async def get_segment_diagnostics(db: AsyncSession = Depends(get_db)):
    segments = (await db.execute(select(RoadSegment))).scalars().all()
    mapped = set((await db.execute(select(CameraRoadSegment.road_segment_id).where(CameraRoadSegment.is_active.is_(True)))).scalars().all())
    observations = (await db.execute(select(SegmentTrafficObservationRecord))).scalars().all()
    calculations = (await db.execute(select(SegmentEmission))).scalars().all()
    latest_observation = {}
    latest_calculation = {}
    for item in observations:
        latest_observation[item.road_segment_id] = max(latest_observation.get(item.road_segment_id, item.captured_at), item.captured_at)
    for item in calculations:
        latest_calculation[item.road_segment_id] = max(latest_calculation.get(item.road_segment_id, item.calculated_at), item.calculated_at)
    return {
        "total_segments": len(segments),
        "segments_with_active_mappings": len(mapped),
        "segments_with_recent_observations": len(latest_observation),
        "segments_with_current_calculations": len(latest_calculation),
        "segments_without_camera_coverage": [s.road_segment_id for s in segments if s.id not in mapped],
        "cameras_without_mappings": [],
        "cameras_with_stale_mappings": [],
        "latest_observation_time_per_segment": {str(k): v for k, v in latest_observation.items()},
        "latest_calculation_time_per_segment": {str(k): v for k, v in latest_calculation.items()},
    }
