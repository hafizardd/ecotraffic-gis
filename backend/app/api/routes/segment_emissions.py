from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
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


def _iso(value):
    return value.isoformat() if value is not None else None


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
        spatial_metadata = segment.spatial_metadata or {}
        population_context = spatial_metadata.get("population_context")
        primary = (population_context or {}).get("primary") or {}
        properties = {"segment_id": segment.road_segment_id, "name": segment.name, "length_km": segment.length_km,
                      "pollutant_totals": None,
                      "volume_per_hour": None, "total_emission_g_h": None,
                      "freshness_status": "unknown", "data_age_seconds": None,
                      "vehicle_count_semantics": "unknown", "source_cameras": [],
                      "population": segment.population, "population_district": primary.get("district_name"),
                      "population_context": population_context,
                      "period_start": None, "period_end": None, "observed_at": None, "calculated_at": None,
                      "source_streams": [], "aggregation_policy": None, "source_observation_count": None,
                      "volume_status": "unavailable", "calculation_version": None}
        if emission:
            pollutant_totals = emission.pollutant_totals_g_h
            freshness = classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings))
            properties.update({"pollutant_totals": pollutant_totals, "volume_per_hour": emission.volume_per_hour,
                               "total_emission_g_h": sum(pollutant_totals.values()) if pollutant_totals else None,
                               "freshness_status": freshness.status.value, "data_age_seconds": freshness.age_seconds,
                               "vehicle_count_semantics": emission.vehicle_count_semantics,
                               "source_cameras": emission.source_cameras,
                               "source_streams": emission.source_streams,
                               "aggregation_policy": emission.aggregation_policy,
                               "source_observation_count": emission.source_observation_count,
                               "volume_status": "estimated" if emission.vehicle_count_semantics == "snapshot_occupancy" else "calculated",
                               "period_start": _iso(emission.period_start), "period_end": _iso(emission.period_end),
                               "observed_at": _iso(emission.period_end), "calculated_at": _iso(emission.calculated_at),
                               "calculation_version": emission.calculation_version})
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    return JSONResponse({"type": "FeatureCollection", "features": features})


@router.get("/api/emissions/map", response_model=list[SegmentEmissionMapItem])
async def get_segment_emission_map(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoadSegment, SegmentEmission)
        .outerjoin(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .order_by(RoadSegment.road_segment_id, SegmentEmission.period_end.desc().nullslast())
    )
    latest = {}
    for segment, emission in result:
        latest.setdefault(segment.road_segment_id, (segment, emission))
    items = []
    for segment, emission in latest.values():
        if emission is None:
            items.append(SegmentEmissionMapItem(
                road_segment_id=segment.road_segment_id,
                total_emission=None, calculated_at=None,
                observed_at=None, data_age_seconds=None, freshness_status="unknown",
                vehicle_count_semantics="unknown", source_cameras=[],
            ))
            continue
        freshness = classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings))
        items.append(SegmentEmissionMapItem(
            road_segment_id=segment.road_segment_id,
            total_emission=(sum(emission.pollutant_totals_g_h.values()) if emission.pollutant_totals_g_h else None),
            calculated_at=emission.calculated_at, observed_at=emission.period_end,
            data_age_seconds=freshness.age_seconds,
            freshness_status=freshness.status.value,
            vehicle_count_semantics=emission.vehicle_count_semantics,
            source_cameras=emission.source_cameras,
        ))
    return items


@router.get("/api/emissions/segments/history")
async def get_segment_emission_history(
    segment_id: str | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    bucket: str = Query(default="hour"),
    db: AsyncSession = Depends(get_db),
):
    """Hourly history view (read-only, no new table in v1).

    hour_bucket = date_trunc('hour', period_end); hourly values use avg()
    (rate samples), never sum().
    """
    if bucket != "hour":
        raise HTTPException(status_code=400, detail="Only bucket=hour is supported in v1.")
    stmt = select(RoadSegment, SegmentEmission).join(
        SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id
    ).order_by(SegmentEmission.period_end)
    if segment_id:
        stmt = stmt.where(RoadSegment.road_segment_id == segment_id)
    for raw, col in ((from_, SegmentEmission.period_end), (to, SegmentEmission.period_end)):
        if raw:
            try:
                bound = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid datetime: {raw}")
            stmt = stmt.where(col >= bound if raw == from_ else col <= bound)
    buckets: dict[str, dict] = {}
    for segment, emission in (await db.execute(stmt)).all():
        totals = emission.pollutant_totals_g_h or {}
        total = sum(float(v) for v in totals.values())
        vol = emission.volume_per_hour or {}
        volume = sum(float(v) for v in vol.values())
        bucket_start = emission.period_end.replace(minute=0, second=0, microsecond=0).isoformat()
        key = (bucket_start, segment.road_segment_id)
        entry = buckets.setdefault(key, {"bucket_start": bucket_start, "segment_id": segment.road_segment_id,
            "total_sum": 0.0, "volume_sum": 0.0, "n": 0})
        entry["total_sum"] += total
        entry["volume_sum"] += volume
        entry["n"] += 1
    return [{"bucket_start": e["bucket_start"], "segment_id": e["segment_id"],
             "avg_total_emission_g_h": e["total_sum"] / e["n"],
             "avg_volume_per_hour": e["volume_sum"] / e["n"],
             "sample_count": e["n"]} for e in buckets.values()]


@router.get("/api/emissions/{road_segment_id}", response_model=SegmentEmissionResponse)
async def get_segment_emission(road_segment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoadSegment, SegmentEmission)
        .outerjoin(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(RoadSegment.road_segment_id == road_segment_id)
        .order_by(SegmentEmission.period_end.desc().nullslast(), SegmentEmission.calculation_version.desc().nullslast())
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Road segment '{road_segment_id}' not found")
    segment, emission = row
    spatial_metadata = segment.spatial_metadata or {}
    population_context = spatial_metadata.get("population_context")
    if emission is None:
        return SegmentEmissionResponse(
            road_segment_id=segment.road_segment_id, name=segment.name, length_km=segment.length_km,
            period_start=None, period_end=None, calculated_at=None, raw_counts=None, volume_per_hour=None,
            vkt_km_h=None, pollutant_totals_g_h=None, category_pollutant_breakdown_g_h=None,
            provenance={},
            volume_status="unavailable", vehicle_count_semantics="unknown", freshness_status="unknown",
            population=segment.population,
            population_district=(population_context or {}).get("primary", {}).get("district_name"),
            population_context=population_context,
        )
    return SegmentEmissionResponse(
        road_segment_id=segment.road_segment_id, name=segment.name, length_km=segment.length_km,
        period_start=emission.period_start, period_end=emission.period_end, calculated_at=emission.calculated_at,
        raw_counts=emission.raw_counts, volume_per_hour=emission.volume_per_hour, vkt_km_h=emission.vkt_km_h,
        pollutant_totals_g_h=emission.pollutant_totals_g_h, category_pollutant_breakdown_g_h=emission.category_pollutant_breakdown_g_h,
        provenance={"source_cameras": emission.source_cameras, "source_streams": emission.source_streams, "aggregation_policy": emission.aggregation_policy},
        volume_status="unavailable" if emission.volume_per_hour is None else ("estimated" if emission.vehicle_count_semantics == "snapshot_occupancy" else "calculated"),
        vehicle_count_semantics=emission.vehicle_count_semantics,
        freshness_status=classify_freshness(emission.period_end, now=datetime.now(timezone.utc), policy=FreshnessPolicy.from_settings(settings)).status.value,
        population=segment.population,
        population_district=(population_context or {}).get("primary", {}).get("district_name") if population_context else None,
        population_context=population_context,
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
