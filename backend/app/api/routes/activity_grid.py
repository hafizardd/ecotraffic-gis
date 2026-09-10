from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.spatial_layers import _feature, _parse_bbox
from app.core.database import get_db
from app.models.activity_grid import ActivityGridHex

router = APIRouter(prefix="/api/spatial", tags=["spatial"])


def _hex_properties(hex_cell: ActivityGridHex) -> dict:
    return {
        "hex_id": hex_cell.hex_id, "luas_km2": hex_cell.luas_km2, "poi_total": hex_cell.poi_total,
        "poi_breakdown": hex_cell.poi_breakdown, "penduduk": hex_cell.penduduk, "volume_mean": hex_cell.volume_mean,
        "norm_volume": hex_cell.norm_volume, "norm_poi": hex_cell.norm_poi, "norm_penduduk": hex_cell.norm_penduduk,
        "skor_total_ahp": hex_cell.skor_total_ahp, "ranking": hex_cell.ranking,
        "klasifikasi_potensi": hex_cell.klasifikasi_potensi, "ahp_weight_version": hex_cell.ahp_weight_version,
        "source": hex_cell.source,
    }


@router.get("/activity-grid")
async def get_activity_grid(bbox: str | None = None, db: AsyncSession = Depends(get_db)):
    bounds = _parse_bbox(bbox)
    query = select(ActivityGridHex, text("ST_AsGeoJSON(activity_grid_hexes.geometry)::json")).order_by(ActivityGridHex.ranking)
    if bounds:
        query = query.where(text("ST_Intersects(activity_grid_hexes.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"))
    params = dict(zip(("min_lon", "min_lat", "max_lon", "max_lat"), bounds)) if bounds else {}
    result = await db.execute(query, params)
    return {"type": "FeatureCollection", "features": [_feature(geometry, _hex_properties(cell)) for cell, geometry in result]}


@router.get("/activity-grid/{hex_id}")
async def get_activity_grid_hex(hex_id: int, db: AsyncSession = Depends(get_db)):
    geometry = (
        await db.execute(
            select(text("ST_AsGeoJSON(activity_grid_hexes.geometry)::json")).where(ActivityGridHex.hex_id == hex_id)
        )
    ).scalar_one_or_none()
    cell = (await db.execute(select(ActivityGridHex).where(ActivityGridHex.hex_id == hex_id))).scalar_one_or_none()
    if cell is None:
        raise HTTPException(status_code=404, detail="Activity grid hex not found")
    return _feature(geometry, _hex_properties(cell))
