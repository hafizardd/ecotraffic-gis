from datetime import datetime, timezone
 
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.core.database import get_db
from app.models.camera import Camera
from app.models.emission import Emission
from app.models.emission_aggregate import EmissionAggregate
from app.schemas.emission import (
    CameraEmissionsResponse,
    EmissionRow,
    EmissionSummaryResponse,
    VehicleSummary,
)
from app.services.emission_aggregation import EMISSION_RATE_FIELDS
from app.services.data_freshness import FreshnessPolicy, classify_freshness
from app.core.config import settings
 
router = APIRouter(tags=["emissions"])

@router.get("/api/cameras/{camera_id}/emissions", response_model=CameraEmissionsResponse)
async def get_camera_emissions(
    camera_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the last N emission records for one camera.
    The frontend chart reads this on panel open.
    """
    # Verify camera exists
    cam_result = await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )
    camera = cam_result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")
 
    # Read aggregated windows plus existing legacy rows. New worker output is
    # aggregate-only, while rows created before this migration remain visible.
    aggregate_result = await db.execute(
        select(EmissionAggregate)
        .where(EmissionAggregate.camera_id == camera.id)
        .order_by(EmissionAggregate.period_end.desc())
        .limit(limit)
    )
    legacy_result = await db.execute(
        select(Emission)
        .where(Emission.camera_id == camera.id)
        .order_by(Emission.timestamp.desc())
        .limit(limit)
    )
    emissions = list(aggregate_result.scalars().all()) + list(
        legacy_result.scalars().all()
    )
    emissions.sort(key=_history_timestamp, reverse=True)
    emissions = emissions[:limit]
    emissions = list(reversed(emissions))  # oldest first for chart
 
    return CameraEmissionsResponse(
        camera_id=camera_id,
        total_records=len(emissions),
        emissions=[EmissionRow.model_validate(e) for e in emissions],
    )

@router.get("/api/emissions/summary", response_model=EmissionSummaryResponse)
async def get_emissions_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns city-wide aggregated stats using the most recent
    emission row from each active camera.
    Used by the global counter at the top of the dashboard.
    """
    camera_result = await db.execute(
        select(
            Camera.id, Camera.data_source, Camera.is_active,
            func.count(EmissionAggregate.id).label("aggregate_count"),
            func.max(EmissionAggregate.period_end).label("latest_observation_at"),
            func.max(EmissionAggregate.period_end).label("latest_processing_at"),
        )
        .outerjoin(EmissionAggregate, EmissionAggregate.camera_id == Camera.id)
        .where(Camera.is_active.is_(True))
        .group_by(Camera.id, Camera.data_source, Camera.is_active)
    )
    camera_rows = camera_result.all()

    if not camera_rows:
        return EmissionSummaryResponse(
            total_cameras_active=0,
            **{field: 0.0 for field in EMISSION_RATE_FIELDS},
            by_vehicle=VehicleSummary(car=0, motorcycle=0, bus=0, truck=0),
            last_updated=None, active_cameras=0,
        )

    # Read current persisted windows in one grouped/window query. Legacy rows are
    # deliberately excluded from the current summary.
    latest_rows = await db.execute(
        select(EmissionAggregate).where(
            EmissionAggregate.id.in_(
                select(func.max(EmissionAggregate.id))
                .group_by(EmissionAggregate.camera_id)
            )
        )
    )
    aggregates = list(latest_rows.scalars().all())
    emission_totals = {field: 0.0 for field in EMISSION_RATE_FIELDS}
    total_car = 0
    total_motorcycle = 0
    total_bus = 0
    total_truck = 0
    last_updated = max((item.period_end for item in aggregates), default=None)
    for emission in aggregates:
        for field in EMISSION_RATE_FIELDS:
            emission_totals[field] += getattr(emission, field)
        total_car += emission.car
        total_motorcycle += emission.motorcycle
        total_bus += emission.bus
        total_truck += emission.truck

    now = datetime.now(timezone.utc)
    freshness = classify_freshness(last_updated, now=now, policy=FreshnessPolicy.from_settings(settings))
    live_cameras = sum(row.data_source == "LIVE" for row in camera_rows)
    historical_cameras = len(camera_rows) - live_cameras
    fresh_states = sum(
        row.latest_observation_at is not None and classify_freshness(
            row.latest_observation_at, now=now, policy=FreshnessPolicy.from_settings(settings)
        ).status.value == "fresh" for row in camera_rows
    )
    stale_states = sum(
        row.latest_observation_at is not None and classify_freshness(
            row.latest_observation_at, now=now, policy=FreshnessPolicy.from_settings(settings)
        ).status.value == "stale" for row in camera_rows
    )
 
    return EmissionSummaryResponse(
        total_cameras_active=len(camera_rows),
        **{
            field: round(value, 2 if field.endswith("g_per_min") else 4)
            for field, value in emission_totals.items()
        },
        by_vehicle=VehicleSummary(
            car=total_car,
            motorcycle=total_motorcycle,
            bus=total_bus,
            truck=total_truck,
        ),
        last_updated=last_updated,
        active_cameras=len(camera_rows), live_cameras=live_cameras,
        historical_cameras=historical_cameras,
        fresh_camera_states=fresh_states, stale_camera_states=stale_states,
        latest_observation_at=last_updated, latest_processing_at=last_updated,
        freshness_status=freshness.status.value,
    )


def _history_timestamp(emission: Emission | EmissionAggregate) -> datetime:
    if isinstance(emission, EmissionAggregate):
        return emission.period_end
    return emission.timestamp
