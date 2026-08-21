from datetime import datetime, timezone
 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.core.config import settings
from app.core.database import get_db
from app.models.camera import Camera
from app.services.data_freshness import FreshnessPolicy, classify_freshness
from app.schemas.camera import (
    CameraFeature,
    CameraFeatureCollection,
    CameraProperties,
    GeoJSONPoint,
)
 
router = APIRouter(prefix="/api/cameras", tags=["cameras"])

@router.get("", response_model=CameraFeatureCollection)
async def get_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Camera,
            text("ST_AsGeoJSON(cameras.location)::json as geojson")
        )
        .where(Camera.is_active == True)
        .order_by(Camera.created_at)
    )
    rows = result.all()
    now = datetime.now(timezone.utc)

    features = []
    for camera, geojson in rows:
        coords = geojson["coordinates"]  # [longitude, latitude]
        features.append(
            CameraFeature(
                geometry=GeoJSONPoint(coordinates=coords),
                properties=_camera_properties(camera, now)
            )
        )

    return CameraFeatureCollection(features=features)

@router.get("/{camera_id}", response_model=CameraProperties)
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns a single camera by its slug (camera_id).
    """
    result = await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )
    camera = result.scalar_one_or_none()
 
    if camera is None:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")
 
    return _camera_properties(camera, datetime.now(timezone.utc))


def _camera_properties(camera: Camera, now: datetime) -> CameraProperties:
    freshness = classify_freshness(
        camera.last_success_at,
        now=now,
        policy=FreshnessPolicy.from_settings(settings),
    )
    return CameraProperties(
        id=camera.id,
        name=camera.name,
        camera_id=camera.camera_id,
        stream_url=camera.stream_url,
        is_active=camera.is_active,
        status=camera.status,
        failure_count=camera.failure_count,
        last_sample_at=camera.last_sample_at,
        last_success_at=camera.last_success_at,
        last_error_at=camera.last_error_at,
        freshness_status=freshness.status.value,
        data_age_seconds=freshness.age_seconds,
        created_at=camera.created_at,
    )
