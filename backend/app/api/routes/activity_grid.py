from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
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
from app.services.hex_h3 import (
    LOD_RESOLUTIONS,
    aggregate_cells,
    h3_boundary_geojson,
    h3_cell,
    in_bbox,
    quantile_breaks,
)
from app.services.spatial_integration import resolve_primary_hex

router = APIRouter(prefix="/api/spatial", tags=["spatial"])

_DAY = timedelta(hours=24)

# GeoJSON coordinate precision. Native cells are ~±100 m, so 5 decimals (~1 m)
# is already below the geometry's own accuracy and trims ~30% off the payload.
_GEOJSON_PRECISION = 5


def _envelope(features: list[dict], breaks, lod: str, resolution: int | None = None) -> dict:
    """GeoJSON collection plus the viewport's dynamic choropleth breaks."""
    return {
        "type": "FeatureCollection",
        "features": features,
        "breaks": breaks,
        "lod": lod,
        "resolution": resolution,
    }


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
    query = select(ActivityGridHex.hex_id, text(f"ST_AsGeoJSON(activity_grid_hexes.geometry, {_GEOJSON_PRECISION})::json"))
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
    return _envelope(features, quantile_breaks([feature["properties"].get("skor_total_ahp") for feature in features]), "fine")


async def _aggregated_grid(db, hour: datetime | None, resolution: int, bounds, lod: str):
    """Zoomed-out LOD: native cells rolled up into H3 cells at ``resolution``.

    Native cells stay the unit of scoring — the H3 geometry and its metrics are
    an area-weighted render approximation, not an independently scored cell, so
    ``hex_id`` is null to block drill-down. ``breaks`` are the viewport's own
    quantiles so the ramp rescales with whatever is on screen.
    """
    rows = (await db.execute(
        select(
            ActivityGridHex,
            text("ST_X(ST_Centroid(activity_grid_hexes.geometry))::float"),
            text("ST_Y(ST_Centroid(activity_grid_hexes.geometry))::float"),
        )
    )).all()
    scores = recompute_hour_scores([row[0] for row in rows], await hourly_hex_volumes(db, hour)) if hour else None

    groups: dict[str, list] = {}
    included: list = []
    for cell, lon, lat in rows:
        # ponytail: viewport filter is centroid-in-bbox, so an edge cell whose
        # centroid is just outside the viewport is dropped. Switch to
        # ST_Intersects prefilter if edge pop becomes visible.
        if not in_bbox(lon, lat, bounds):
            continue
        included.append(cell)
        groups.setdefault(h3_cell(lon, lat, resolution), []).append((cell, lon, lat))

    features = []
    for cell_id, members in groups.items():
        aggregate = aggregate_cells(members, scores)
        features.append(_feature({"type": "Polygon", "coordinates": [h3_boundary_geojson(cell_id)]}, {
            "hex_id": None, "h3_index": cell_id, "luas_km2": aggregate["luas_km2"],
            "poi_total": aggregate["poi_total"], "poi_breakdown": {}, "penduduk": aggregate["penduduk"],
            "volume_mean": 0.0, "norm_volume": None, "norm_poi": 0.0, "norm_penduduk": 0.0,
            "skor_total_ahp": aggregate["skor_total_ahp"], "ranking": None,
            "klasifikasi_potensi": aggregate["klasifikasi_potensi"], "ahp_weight_version": "h3-aggregated",
            "source": "aggregated", "data_status": "live" if hour else "static",
            "aggregated_count": len(members), "resolution": resolution,
        }))
    breaks = quantile_breaks([
        (scores.get(cell.hex_id, {}).get("skor_total_ahp") if scores is not None else cell.skor_total_ahp)
        for cell in included
    ])
    return _envelope(features, breaks, lod, resolution)


@router.get("/activity-grid")
async def get_activity_grid(response: Response, bbox: str | None = None, hour: str | None = None, lod: str | None = None,
                            db: AsyncSession = Depends(get_db)):
    # The grid only changes when a new hour bucket lands, so let the browser (and
    # any intermediary keyed on the full bbox/hour/lod URL) reuse the snapshot
    # briefly instead of re-downloading it on every pan back-and-forth.
    response.headers["Cache-Control"] = "public, max-age=30"
    bounds = _parse_bbox(bbox)
    resolution = LOD_RESOLUTIONS.get(lod or "")
    if resolution is not None:
        return await _aggregated_grid(db, _parse_hour(hour) if hour else None, resolution, bounds, lod)
    if hour:
        return await _live_grid(db, _parse_hour(hour), bounds)
    # Bare request: the static offline snapshot, byte-for-byte unchanged.
    query = select(ActivityGridHex, text(f"ST_AsGeoJSON(activity_grid_hexes.geometry, {_GEOJSON_PRECISION})::json")).order_by(ActivityGridHex.ranking)
    if bounds:
        query = query.where(text("ST_Intersects(activity_grid_hexes.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"))
    result = await db.execute(query, _bbox_params(bounds))
    features = [_feature(geometry, _hex_properties(cell)) for cell, geometry in result]
    return _envelope(features, quantile_breaks([feature["properties"].get("skor_total_ahp") for feature in features]), "fine")


async def _available_hours(db) -> list[datetime]:
    """Hour buckets with at least one observed segment sample in the last 24h."""
    bucket = func.to_timestamp(func.floor(func.extract("epoch", SegmentEmission.period_start) / 3600) * 3600).label("hour")
    statement = (
        select(bucket)
        .where(SegmentEmission.period_start >= datetime.now(timezone.utc) - _DAY,
               source_mode_expression().notin_(["SYNTHETIC", "REPLAY"]))
        .distinct()
        .order_by(bucket)
    )
    return [moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
            for moment in (await db.execute(statement)).scalars().all()]


@router.get("/activity-grid/available-hours")
async def get_activity_grid_available_hours(db: AsyncSession = Depends(get_db)):
    """Hour buckets with at least one observed segment sample in the last 24h.

    Sizes the time slider; the frontend must not probe for availability.
    """
    hours = [moment.isoformat() for moment in await _available_hours(db)]
    return {"hours": hours, "earliest": hours[0] if hours else None, "latest": hours[-1] if hours else None}


@router.get("/activity-grid/{hex_id}/hourly")
async def get_activity_grid_hex_hourly(hex_id: int, db: AsyncSession = Depends(get_db)):
    """One hex's live score across every available hour bucket (24h pattern).

    The whole grid is re-scored per hour so min/max normalization matches the
    map; the response is just the selected hex's slice.
    """
    cells = (await db.execute(select(ActivityGridHex))).scalars().all()
    if not any(cell.hex_id == hex_id for cell in cells):
        raise HTTPException(status_code=404, detail="Activity grid hex not found")
    series = []
    for moment in await _available_hours(db):
        scores = recompute_hour_scores(cells, await hourly_hex_volumes(db, moment))
        entry = scores.get(hex_id, dict(NO_DATA))
        series.append({
            "hour": moment.isoformat(),
            "skor_total_ahp": entry.get("skor_total_ahp"),
            "norm_volume": entry.get("norm_volume"),
            "klasifikasi_potensi": entry.get("klasifikasi_potensi"),
            "data_status": entry.get("data_status"),
        })
    return {"hex_id": hex_id, "series": series}


@router.get("/activity-grid/{hex_id}")
async def get_activity_grid_hex(hex_id: int, hour: str | None = None, db: AsyncSession = Depends(get_db)):
    geometry = (
        await db.execute(
            select(text(f"ST_AsGeoJSON(activity_grid_hexes.geometry, {_GEOJSON_PRECISION})::json")).where(ActivityGridHex.hex_id == hex_id)
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
            select(text(f"ST_AsGeoJSON(activity_grid_hexes.geometry, {_GEOJSON_PRECISION})::json")).where(ActivityGridHex.hex_id == cell.hex_id)
        )
    ).scalar_one()
    return _feature(geometry, _hex_properties(cell))
