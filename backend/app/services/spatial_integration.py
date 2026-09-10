"""Deterministic spatial criterion calculations backed by imported source layers."""

from collections import Counter
from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select

from app.models.road_segment import RoadSegment
from app.models.spatial_sources import PointOfInterest, PopulationZone, SurveyStopObservation

K3_BUFFER_M = 400
K4_BUFFER_M = 500
K5_BUFFER_M = 500
SURVEY_SCORING_VERSION = "survey-keyword-v1"
POI_WEIGHT_VERSION = "poi-category-v1"
POI_CATEGORY_WEIGHTS = {
    "Pendidikan": 1.25, "Kesehatan": 1.25, "Pariwisata": 1.15, "Perdagangan": 1.2,
    "Kuliner": 1.0, "Perkantoran": 1.0, "Pemerintahan": 1.0, "Peribadatan": 0.7, "Transportasi": 1.1,
}

_geog = Geography(srid=4326)


def _keyword_score(text: str | None, keywords: tuple[str, ...]) -> float | None:
    if not text:
        return None
    value = text.casefold()
    hits = sum(keyword in value for keyword in keywords)
    return min(5.0, 1.0 + hits) if hits else None


def score_survey_description(description: str | None) -> dict[str, float | None]:
    """Extract conservative 1-5 evidence scores; ambiguous evidence stays unavailable."""
    return {
        "facility": _keyword_score(description, ("shelter", "halte", "bangku", "penerangan", "lampu", "rambu")),
        "pedestrian_access": _keyword_score(description, ("trotoar", "menyeberang", "ramp", "akses", "parkir", "drainase")),
        "environment": _keyword_score(description, ("bersih", "sampah", "vandalisme", "rusak", "nyaman", "lingkungan")),
        "user_activity": _keyword_score(description, ("penumpang", "pengguna", "menunggu", "bus", "petugas")),
    }


def _normalize(value: float | None, value_range: tuple[float, float] | None, *, invert: bool = False) -> float | None:
    if value is None or value_range is None:
        return None
    low, high = value_range
    normalized = 0.0 if low == high else (value - low) / (high - low)
    return 1.0 - normalized if invert else normalized


def _empty_result() -> dict:
    return {
        "K3": None, "K4": None, "K5": None, "population_context": None,
        "raw_values": {"K3": None, "K4": None, "K5": None}, "normalized_values": {},
        "component_status": {"K3": "pending", "K4": "pending", "K5": "pending"},
        "provenance": {
            "sources": [], "buffer_distances_m": {"K3": K3_BUFFER_M, "K4": K4_BUFFER_M, "K5": K5_BUFFER_M},
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "scoring_versions": {"K3": SURVEY_SCORING_VERSION, "K4": POI_WEIGHT_VERSION},
        },
    }


def compute_population_context(db, segment) -> dict | None:
    centroid = func.ST_Centroid(RoadSegment.geometry)
    primary = db.execute(
        select(PopulationZone).where(
            RoadSegment.id == segment.id, func.ST_Within(centroid, PopulationZone.geometry)
        ).limit(1)
    ).scalar_one_or_none()

    buffer_geog = func.ST_Buffer(cast(RoadSegment.geometry, _geog), K5_BUFFER_M)
    zone_geog = cast(PopulationZone.geometry, _geog)
    share = (
        func.ST_Area(func.ST_Intersection(buffer_geog, zone_geog))
        / func.nullif(func.ST_Area(buffer_geog), 0)
    ).label("overlap_share")
    zones = db.execute(
        select(PopulationZone, share).where(
            RoadSegment.id == segment.id, func.ST_Intersects(buffer_geog, zone_geog)
        )
    ).all()

    if primary is None and not zones:
        return None
    intersecting = [{"district_name": zone.district_name, "population": zone.population, "overlap_share": float(share or 0)} for zone, share in zones]
    return {
        "primary": ({"district_name": primary.district_name, "population": primary.population, "method": "segment_centroid_within"} if primary else None),
        "intersecting": intersecting, "buffer_distance_m": K5_BUFFER_M, "source": "populations.geojson",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def compute_k3_for_segment(db, segment) -> dict:
    rows = db.execute(
        select(SurveyStopObservation).where(
            RoadSegment.id == segment.id,
            func.ST_DWithin(cast(RoadSegment.geometry, _geog), cast(SurveyStopObservation.geometry, _geog), K3_BUFFER_M),
        )
    ).scalars().all()
    scored = []
    for row in rows:
        evidence = score_survey_description(row.description)
        components = [evidence[key] for key in ("facility", "pedestrian_access", "environment") if evidence[key] is not None]
        condition = sum(components) / len(components) if components else None
        user = evidence["user_activity"]
        if row.manual_score_override is not None:
            score = row.manual_score_override
        elif condition is not None and user is not None:
            score = 0.7 * condition + 0.3 * user
        else:
            score = condition or user
        if score is not None:
            scored.append((score, row))
    if not scored:
        return {"value": None, "details": {"nearby_observation_count": len(rows), "status": "pending", "scoring_version": SURVEY_SCORING_VERSION}}
    composite = sum(score for score, _ in scored) / len(scored)
    return {
        "value": composite,
        "details": {
            "nearby_observation_count": len(rows), "composite_stop_score": composite,
            "source_ids": [row.source_id for _, row in scored],
            "observed_at": [row.observed_at.isoformat() for _, row in scored if row.observed_at],
            "status": "complete", "scoring_version": SURVEY_SCORING_VERSION,
        },
    }


def compute_k4_for_segment(db, segment) -> dict:
    rows = db.execute(
        select(PointOfInterest).where(
            RoadSegment.id == segment.id,
            func.ST_DWithin(cast(RoadSegment.geometry, _geog), cast(PointOfInterest.geometry, _geog), K4_BUFFER_M),
        )
    ).scalars().all()
    categories = Counter(row.category or "Tidak diketahui" for row in rows)
    weighted = sum(POI_CATEGORY_WEIGHTS.get(category, 0.8) * count for category, count in categories.items())
    return {
        "value": weighted / max(segment.length_km, 0.001),
        "details": {
            "poi_count": len(rows), "category_counts": dict(categories), "weighted_poi_count": weighted,
            "buffer_distance_m": K4_BUFFER_M, "weight_version": POI_WEIGHT_VERSION, "status": "complete",
        },
    }


def compute_stop_accessibility(db, stop: SurveyStopObservation) -> dict:
    """POI count within K4_BUFFER_M of the stop itself (mirrors compute_k4_for_segment)."""
    rows = db.execute(
        select(PointOfInterest).where(
            SurveyStopObservation.id == stop.id,
            func.ST_DWithin(
                cast(SurveyStopObservation.geometry, _geog), cast(PointOfInterest.geometry, _geog), K4_BUFFER_M
            ),
        )
    ).scalars().all()
    categories = Counter(row.category or "Tidak diketahui" for row in rows)
    weighted = sum(POI_CATEGORY_WEIGHTS.get(category, 0.8) * count for category, count in categories.items())
    return {
        "poi_count": len(rows), "category_counts": dict(categories), "weighted_score": weighted,
        "buffer_distance_m": K4_BUFFER_M, "weight_version": POI_WEIGHT_VERSION,
    }


def compute_k5_for_segment(db, segment, population_context: dict | None) -> dict:
    if not population_context or not population_context.get("intersecting"):
        return {"value": None, "details": {"status": "pending", "method": "areal_weighted_population_density"}}
    context_area_km2 = max((K5_BUFFER_M * 2 / 1000) * max(segment.length_km, 0.001), 0.0001)
    estimate = sum(item["population"] * item["overlap_share"] for item in population_context["intersecting"])
    return {
        "value": estimate / context_area_km2,
        "details": {
            "population_overlap_estimate": estimate, "context_area_km2": context_area_km2,
            "method": "areal_weighted_population_density_estimate", "source_granularity": "kecamatan", "status": "complete",
        },
    }


def compute_all_spatial_criteria(db, segment, *, criterion_ranges: dict[str, tuple[float, float]] | None = None) -> dict:
    result = _empty_result()
    k3 = compute_k3_for_segment(db, segment)
    k4 = compute_k4_for_segment(db, segment)
    context = compute_population_context(db, segment)
    k5 = compute_k5_for_segment(db, segment, context)
    values = {"K3": k3["value"], "K4": k4["value"], "K5": k5["value"]}
    result.update(values)
    result["raw_values"] = values
    result["population_context"] = context
    result["normalized_values"] = {
        key: _normalize(value, (criterion_ranges or {}).get(key), invert=key == "K3")
        for key, value in values.items()
    }
    result["component_status"] = {key: ("complete" if value is not None else "pending") for key, value in values.items()}
    result["spatial_criteria_details"] = {"K3": k3["details"], "K4": k4["details"], "K5": k5["details"]}
    result["provenance"]["sources"] = ["activities.csv", "poi.geojson", "populations.geojson"]
    return result
