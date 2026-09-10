"""Assemble the real, evidence-grounded context object Bang Jo narrates.

Every field is a real query. Missing pieces stay ``None``/empty — nothing is
fabricated — matching the existing ``_empty_result()``/``"status": "pending"``
convention.
"""

from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.models.spatial_sources import SurveyStopObservation
from app.services.spatial_integration import K4_BUFFER_M

_geog = Geography(srid=4326)
HIGH_POTENTIAL = ("Sangat Tinggi", "Tinggi")
DOMINANT_POI_LIMIT = 5


async def build_context(db: AsyncSession, road_segment_id: str) -> dict | None:
    row = (
        await db.execute(
            select(RoadSegment, SegmentEmission)
            .outerjoin(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
            .where(RoadSegment.road_segment_id == road_segment_id)
            .order_by(SegmentEmission.period_end.desc().nullslast())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    segment, emission = row

    segment_geom = select(RoadSegment.geometry).where(RoadSegment.road_segment_id == road_segment_id).scalar_subquery()
    hexes = (
        await db.execute(select(ActivityGridHex).where(func.ST_Intersects(ActivityGridHex.geometry, segment_geom)))
    ).scalars().all()

    stop_rows = (
        await db.execute(
            select(
                SurveyStopObservation,
                func.ST_Distance(cast(RoadSegment.geometry, _geog), cast(SurveyStopObservation.geometry, _geog)).label("distance_m"),
            )
            .select_from(SurveyStopObservation, RoadSegment)
            .where(RoadSegment.road_segment_id == road_segment_id)
            .where(func.ST_DWithin(cast(RoadSegment.geometry, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M))
        )
    ).all()

    dominant = {}
    for hex_cell in hexes:
        for category, count in (hex_cell.poi_breakdown or {}).items():
            dominant[category] = dominant.get(category, 0) + int(count)
    dominant_sorted = sorted(dominant.items(), key=lambda item: item[1], reverse=True)[:DOMINANT_POI_LIMIT]

    no_stop_near_high_hex = ~(
        select(SurveyStopObservation.id)
        .where(
            func.ST_DWithin(
                cast(ActivityGridHex.geometry, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M
            )
        )
        .exists()
    )
    gap_count = (
        await db.execute(
            select(func.count())
            .select_from(ActivityGridHex)
            .where(
                ActivityGridHex.klasifikasi_potensi.in_(HIGH_POTENTIAL),
                func.ST_Intersects(ActivityGridHex.geometry, segment_geom),
                no_stop_near_high_hex,
            )
        )
    ).scalar() or 0

    scores = [hex_cell.skor_total_ahp for hex_cell in hexes]
    activity_potential = {
        "hex_count": len(hexes),
        "hex_ids": [hex_cell.hex_id for hex_cell in hexes],
        "avg_skor_total_ahp": round(sum(scores) / len(scores), 4) if scores else None,
        "max_skor_total_ahp": max(scores) if scores else None,
        "klasifikasi_potensi": sorted({hex_cell.klasifikasi_potensi for hex_cell in hexes}) or None,
        "dominant_poi_categories": [{"category": category, "count": count} for category, count in dominant_sorted],
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segment": {
            "road_segment_id": segment.road_segment_id, "name": segment.name, "length_km": segment.length_km,
            "decision_score": emission.decision_score if emission else None,
            "priority": emission.priority if emission else None,
            "pollutant_totals": emission.pollutant_totals_g_h if emission else None,
            "raw_criteria": emission.raw_criteria if emission else None,
            "data_source": emission.vehicle_count_semantics if emission else None,
            "observed_at": emission.period_end.isoformat() if emission else None,
        },
        "activity_potential": activity_potential,
        "bus_stops": [
            {
                "source_id": stop.source_id, "title": stop.title, "intervention_class": stop.intervention_class,
                "intervention_rank": stop.intervention_rank, "accessibility_score": stop.accessibility_score,
                "facility_score": stop.facility_score, "environment_score": stop.environment_score,
                "distance_to_segment_m": round(float(distance), 1) if distance is not None else None,
            }
            for stop, distance in stop_rows
        ],
        "coverage_gap": bool(gap_count),
    }
