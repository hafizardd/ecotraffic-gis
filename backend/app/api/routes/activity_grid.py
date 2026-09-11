from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.spatial_layers import _feature, _parse_bbox
from app.core.database import get_db
from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.services.emission_analytics import source_mode_expression
from app.services.hex_activity_scoring import (
    NO_DATA,
    hourly_hex_volumes,
    recompute_hour_scores,
)
from app.services.spatial_integration import resolve_primary_hex

router = APIRouter(prefix="/api/spatial", tags=["spatial"])

_DAY = timedelta(hours=24)


def _hex_properties(hex_cell: ActivityGridHex) -> dict:
    return {
        "hex_id": hex_cell.hex_id, "luas_km2": hex_cell.luas_km2, "poi_total": hex_cell.poi_total,
        "poi_breakdown": hex_cell.poi_breakdown, "penduduk": hex_cell.penduduk, "volume_mean": hex_cell.volume_mean,
        "norm_volume": hex_cell.norm_volume, "norm_poi": hex_cell.norm_poi, "norm_penduduk": hex_cell.norm_penduduk,
        "skor_total_ahp": hex_cell.skor_total_ahp, "ranking": hex_cell.ranking,
        "klasifikasi_potensi": hex_cell.klasifikasi_potensi, "ahp_weight_version": hex_cell.ahp_weight_version,
        "source": hex_cell.source,
    }


def _parse_hour(value: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="hour must be an ISO timestamp")
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _bbox_params(bounds) -> dict:
    return dict(zip(("min_lon", "min_lat", "max_lon", "max_lat"), bounds)) if bounds else {}


async def _geometry_rows(db, bounds):
    query = select(ActivityGridHex.hex_id, text("ST_AsGeoJSON(activity_grid_hexes.geometry)::json"))
    if bounds:
        query = query.where(text("ST_Intersects(activity_grid_hexes.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"))
    return await db.execute(query, _bbox_params(bounds))


async def _hour_scores(db, hour: datetime):
    """Global (whole-grid) live scores for one hour, so map and panel agree."""
    cells = (await db.execute(select(ActivityGridHex))).scalars().all()
    scores = recompute_hour_scores(cells, await hourly_hex_volumes(db, hour))
    return cells, scores


async def _live_grid(db, hour: datetime, bounds):
    """Static POI/population + live hourly volume, re-ranked for one hour bucket."""
    cells, scores = await _hour_scores(db, hour)
    cells_by_id = {cell.hex_id: cell for cell in cells}
    features = []
    for hex_id, geometry in await _geometry_rows(db, bounds):
        properties = _hex_properties(cells_by_id[hex_id])
        properties.update(scores.get(hex_id, dict(NO_DATA)))
        features.append(_feature(geometry, properties))
    return {"type": "FeatureCollection", "features": features}


@router.get("/activity-grid")
async def get_activity_grid(bbox: str | None = None, hour: str | None = None,
                            db: AsyncSession = Depends(get_db)):
    bounds = _parse_bbox(bbox)
    if hour:
        return await _live_grid(db, _parse_hour(hour), bounds)
    # Bare request: the static offline snapshot, byte-for-byte unchanged.
    query = select(ActivityGridHex, text("ST_AsGeoJSON(activity_grid_hexes.geometry)::json")).order_by(ActivityGridHex.ranking)
    if bounds:
        query = query.where(text("ST_Intersects(activity_grid_hexes.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"))
    result = await db.execute(query, _bbox_params(bounds))
    return {"type": "FeatureCollection", "features": [_feature(geometry, _hex_properties(cell)) for cell, geometry in result]}


@router.get("/activity-grid/available-hours")
async def get_activity_grid_available_hours(db: AsyncSession = Depends(get_db)):
    """Hour buckets with at least one observed segment sample in the last 24h.

    Sizes the time slider; the frontend must not probe for availability.
    """
    bucket = func.to_timestamp(func.floor(func.extract("epoch", SegmentEmission.period_start) / 3600) * 3600).label("hour")
    statement = (
        select(bucket)
        .where(SegmentEmission.period_start >= datetime.now(timezone.utc) - _DAY,
               source_mode_expression().notin_(["SYNTHETIC", "REPLAY"]))
        .distinct()
        .order_by(bucket)
    )
    hours = [
        moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()
        for moment in (await db.execute(statement)).scalars().all()
    ]
    return {"hours": hours, "earliest": hours[0] if hours else None, "latest": hours[-1] if hours else None}


@router.get("/activity-grid/{hex_id}")
async def get_activity_grid_hex(hex_id: int, hour: str | None = None, db: AsyncSession = Depends(get_db)):
    geometry = (
        await db.execute(
            select(text("ST_AsGeoJSON(activity_grid_hexes.geometry)::json")).where(ActivityGridHex.hex_id == hex_id)
        )
    ).scalar_one_or_none()
    cell = (await db.execute(select(ActivityGridHex).where(ActivityGridHex.hex_id == hex_id))).scalar_one_or_none()
    if cell is None:
        raise HTTPException(status_code=404, detail="Activity grid hex not found")
    properties = _hex_properties(cell)
    if hour:
        _, scores = await _hour_scores(db, _parse_hour(hour))
        properties.update(scores.get(hex_id, dict(NO_DATA)))
    return _feature(geometry, properties)


@router.get("/segments/{road_segment_id}/activity-grid")
async def get_segment_activity_grid(road_segment_id: str, db: AsyncSession = Depends(get_db)):
    """Activity-potential hex containing the segment's longest intersection.

    A 404 means "not covered by the grid" and is a normal empty state for the
    segment panel, not an error.
    """
    segment = (
        await db.execute(select(RoadSegment).where(RoadSegment.road_segment_id == road_segment_id))
    ).scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail=f"Road segment '{road_segment_id}' not found")
    cell = await resolve_primary_hex(db, segment)
    if cell is None:
        raise HTTPException(status_code=404, detail="Segment is not covered by the activity grid")
    geometry = (
        await db.execute(
            select(text("ST_AsGeoJSON(activity_grid_hexes.geometry)::json")).where(ActivityGridHex.hex_id == cell.hex_id)
        )
    ).scalar_one()
    return _feature(geometry, _hex_properties(cell))
