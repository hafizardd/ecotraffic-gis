from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from sqlalchemy import cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.spatial_sources import PointOfInterest, PopulationZone, SurveyStopObservation
from app.services.spatial_integration import K4_BUFFER_M

router = APIRouter(prefix="/api/spatial", tags=["spatial"])

_geog = Geography(srid=4326)


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
    return {"type": "FeatureCollection", "features": [_feature(geometry, {
        "source_id": stop.source_id, "title": stop.title, "score": stop.survey_score or stop.manual_score_override,
        "observed_at": stop.observed_at.isoformat() if stop.observed_at else None, "media_count": len(stop.media or []),
        "facility_score": stop.facility_score, "environment_score": stop.environment_score,
        "accessibility_score": stop.accessibility_score, "intervention_score": stop.intervention_score,
        "intervention_rank": stop.intervention_rank, "intervention_class": stop.intervention_class,
    }) for stop, geometry in result]}


@router.get("/survey-stops/{source_id}")
async def get_survey_stop(source_id: str, db: AsyncSession = Depends(get_db)):
    stop = (await db.execute(select(SurveyStopObservation).where(SurveyStopObservation.source_id == source_id))).scalar_one_or_none()
    if stop is None:
        raise HTTPException(status_code=404, detail="Survey stop not found")
    poi_rows = (
        await db.execute(
            select(PointOfInterest.category, func.count())
            .select_from(PointOfInterest, SurveyStopObservation)
            .where(SurveyStopObservation.source_id == source_id)
            .where(func.ST_DWithin(cast(SurveyStopObservation.geometry, _geog), cast(PointOfInterest.geometry, _geog), K4_BUFFER_M))
            .group_by(PointOfInterest.category)
        )
    ).all()
    return {
        "source_id": stop.source_id, "title": stop.title, "description": stop.description, "observed_at": stop.observed_at,
        "media": stop.media, "observer_name": stop.observer_name,
        "facility_score": stop.facility_score, "pedestrian_access_score": stop.pedestrian_access_score,
        "environment_score": stop.environment_score, "user_activity_score": stop.user_activity_score,
        "survey_score": stop.survey_score, "score_method": stop.score_method,
        "accessibility_score": stop.accessibility_score, "intervention_score": stop.intervention_score,
        "intervention_rank": stop.intervention_rank, "intervention_class": stop.intervention_class,
        "accessibility_score_100": stop.accessibility_score_100, "condition_score_100": stop.condition_score_100,
        "environment_score_100": stop.environment_score_100, "ahp_total_score": stop.ahp_total_score,
        "ahp_rank": stop.ahp_rank, "ahp_classification": stop.ahp_classification,
        "ahp_weight_version": stop.ahp_weight_version, "facility_checklist": stop.facility_checklist,
        "damage_indicators": stop.damage_indicators, "poi_breakdown_survey": stop.poi_breakdown_survey,
        "accessibility_breakdown": [{"category": category, "count": count} for category, count in poi_rows],
        "accessibility_buffer_m": K4_BUFFER_M,
    }
