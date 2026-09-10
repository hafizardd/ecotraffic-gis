"""Spatial context used by segments and bus stops.

Segment decision-scoring (the old K3/K4/K5 AHP pipeline) has been retired;
activity-potential now lives on :class:`ActivityGridHex`. What remains here is
the informational population context, bus-stop accessibility, and the
segment -> primary-hex lookup.
"""

from collections import Counter
from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.spatial_sources import PointOfInterest, PopulationZone, SurveyStopObservation

POPULATION_CONTEXT_BUFFER_M = 500
K4_BUFFER_M = 500
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


def compute_population_context(db, segment) -> dict | None:
    centroid = func.ST_Centroid(RoadSegment.geometry)
    primary = db.execute(
        select(PopulationZone).where(
            RoadSegment.id == segment.id, func.ST_Within(centroid, PopulationZone.geometry)
        ).limit(1)
    ).scalar_one_or_none()

    buffer_geog = func.ST_Buffer(cast(RoadSegment.geometry, _geog), POPULATION_CONTEXT_BUFFER_M)
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
        "intersecting": intersecting, "buffer_distance_m": POPULATION_CONTEXT_BUFFER_M, "source": "populations.geojson",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def compute_stop_accessibility(db, stop: SurveyStopObservation) -> dict:
    """POI count within K4_BUFFER_M of the stop itself (used by bus-stop scoring)."""
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


async def resolve_primary_hex(db, segment) -> ActivityGridHex | None:
    """Return the hex with the longest intersection against the segment geometry.

    ``None`` when the segment lies outside the imported grid coverage. A single
    deterministic hex is picked so the segment panel always shows one cell.
    """
    overlap = func.ST_Length(func.ST_Intersection(ActivityGridHex.geometry, RoadSegment.geometry))
    return (await db.execute(
        select(ActivityGridHex)
        .where(RoadSegment.id == segment.id, func.ST_Intersects(ActivityGridHex.geometry, RoadSegment.geometry))
        .order_by(overlap.desc())
        .limit(1)
    )).scalar_one_or_none()
