from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.spatial_sources import PointOfInterest, PopulationZone, SurveyStopObservation

router = APIRouter(prefix="/api/spatial", tags=["spatial"])


def _parse_bbox(value: str | None):
    if not value:
        return None
    try:
        bounds = tuple(float(item) for item in value.split(","))
    except ValueError:
        raise HTTPException(status_code=422, detail="bbox must be minLon,minLat,maxLon,maxLat")
    if len(bounds) != 4 or bounds[0] >= bounds[2] or bounds[1] >= bounds[3] or not (-180 <= bounds[0] <= bounds[2] <= 180 and -90 <= bounds[1] <= bounds[3] <= 90):
        raise HTTPException(status_code=422, detail="bbox must be a valid geographic extent")
    return bounds


def _feature(geometry, properties):
    return {"type": "Feature", "geometry": geometry, "properties": properties}


@router.get("/pois")
async def get_pois(bbox: str | None = None, category: str | None = None, limit: int = Query(500, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    bounds = _parse_bbox(bbox)
    query = select(PointOfInterest, text("ST_AsGeoJSON(points_of_interest.geometry)::json")).order_by(PointOfInterest.name).limit(limit)
    if bounds:
        query = query.where(text("ST_Intersects(points_of_interest.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"))
    if category:
        query = query.where(PointOfInterest.category == category)
    params = dict(zip(("min_lon", "min_lat", "max_lon", "max_lat"), bounds)) if bounds else {}
    result = await db.execute(query, params)
    return {"type": "FeatureCollection", "features": [_feature(geometry, {"name": poi.name, "category": poi.category, "type_1": poi.type_1, "type_2": poi.type_2, "type_3": poi.type_3, "address": poi.address}) for poi, geometry in result]}


@router.get("/population-zones")
async def get_population_zones(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PopulationZone, text("ST_AsGeoJSON(population_zones.geometry)::json")))
    return {"type": "FeatureCollection", "features": [_feature(geometry, {"district_name": zone.district_name, "population": zone.population, "source": zone.source, "reference_year": zone.reference_year}) for zone, geometry in result]}


@router.get("/survey-stops")
async def get_survey_stops(bbox: str | None = None, limit: int = Query(200, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    bounds = _parse_bbox(bbox)
    query = select(SurveyStopObservation, text("ST_AsGeoJSON(survey_stop_observations.geometry)::json")).order_by(SurveyStopObservation.observed_at.desc().nullslast()).limit(limit)
    if bounds:
        query = query.where(text("ST_Intersects(survey_stop_observations.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"))
    params = dict(zip(("min_lon", "min_lat", "max_lon", "max_lat"), bounds)) if bounds else {}
    result = await db.execute(query, params)
    return {"type": "FeatureCollection", "features": [_feature(geometry, {"source_id": stop.source_id, "title": stop.title, "score": stop.survey_score or stop.manual_score_override, "observed_at": stop.observed_at.isoformat() if stop.observed_at else None, "media_count": len(stop.media or [])}) for stop, geometry in result]}


@router.get("/survey-stops/{source_id}")
async def get_survey_stop(source_id: str, db: AsyncSession = Depends(get_db)):
    stop = (await db.execute(select(SurveyStopObservation).where(SurveyStopObservation.source_id == source_id))).scalar_one_or_none()
    if stop is None:
        raise HTTPException(status_code=404, detail="Survey stop not found")
    return {"source_id": stop.source_id, "title": stop.title, "description": stop.description, "observed_at": stop.observed_at, "media": stop.media, "observer_name": stop.observer_name}
