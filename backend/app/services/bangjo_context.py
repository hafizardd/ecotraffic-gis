"""Assemble the real, evidence-grounded context object Bang Jo narrates.

Every field is a real query. Missing pieces stay ``None``/empty — nothing is
fabricated — matching the existing ``_empty_result()``/``"status": "pending"``
convention.
"""

from datetime import datetime, timedelta, timezone
from collections import Counter

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.models.spatial_sources import SurveyStopObservation
from app.services.spatial_integration import K4_BUFFER_M
from cv.proposal_emission_factors import POLLUTANTS

_geog = Geography(srid=4326)
HIGH_POTENTIAL = ("Sangat Tinggi", "Tinggi")
WEAK_CLASSES = ("Rendah", "Sangat Rendah")
DOMINANT_POI_LIMIT = 5
REPLAY_WINDOW_HOURS = 24


def _hourly_point(emission: SegmentEmission) -> dict:
    """One precomputed REPLAY hour, interpolation flags included."""
    metadata = emission.ahp_metadata or {}
    calc_meta = metadata.get("calculation_metadata") or {}
    totals = emission.pollutant_totals_g_h or {}
    return {
        "hour": emission.period_start.isoformat(),
        "emissions_kg_h": {
            pollutant.lower(): (totals[pollutant] / 1000 if totals.get(pollutant) is not None else None)
            for pollutant in POLLUTANTS
        },
        "volume_per_hour": emission.volume_per_hour,
        "is_interpolated": bool(calc_meta.get("is_interpolated")),
        "interpolation_method": calc_meta.get("interpolation_method"),
    }


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
                func.ST_Distance(cast(segment_geom, _geog), cast(SurveyStopObservation.geometry, _geog)).label("distance_m"),
            )
            .where(func.ST_DWithin(cast(segment_geom, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M))
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
    primary_hex = max(hexes, key=lambda hex_cell: hex_cell.skor_total_ahp) if hexes else None
    activity_potential = {
        "hex_count": len(hexes),
        "hex_ids": [hex_cell.hex_id for hex_cell in hexes],
        "avg_skor_total_ahp": round(sum(scores) / len(scores), 4) if scores else None,
        "max_skor_total_ahp": max(scores) if scores else None,
        "klasifikasi_potensi": sorted({hex_cell.klasifikasi_potensi for hex_cell in hexes}) or None,
        "dominant_poi_categories": [{"category": category, "count": count} for category, count in dominant_sorted],
    }

    stop_classes = [stop.intervention_class for stop, _ in stop_rows if stop.intervention_class]
    stop_scores = [getattr(stop, "ahp_total_score", None) for stop, _ in stop_rows]
    stop_scores = [score for score in stop_scores if score is not None]
    weak_stop_count = sum(1 for label in stop_classes if label in WEAK_CLASSES)
    activity_class = primary_hex.klasifikasi_potensi if primary_hex else None
    coverage_gap = bool(gap_count)
    if coverage_gap:
        intervention_hint = "add_new_stop"
    elif weak_stop_count:
        intervention_hint = "improve_existing_stop"
    elif activity_class in HIGH_POTENTIAL:
        intervention_hint = "increase_frequency"
    else:
        intervention_hint = None
    stop_assessment = {
        "count": len(stop_rows),
        "scored_count": len(stop_scores),
        "class_counts": dict(Counter(stop_classes)),
        "weak_stop_count": weak_stop_count,
        "min_ahp_total_score": round(min(stop_scores), 4) if stop_scores else None,
        "avg_ahp_total_score": round(sum(stop_scores) / len(stop_scores), 4) if stop_scores else None,
    }

    replay_rows = (
        await db.execute(
            select(SegmentEmission)
            .where(
                SegmentEmission.road_segment_id == segment.id,
                SegmentEmission.ahp_metadata["source_mode"].astext == "REPLAY",
                SegmentEmission.period_start >= datetime.now(timezone.utc) - timedelta(hours=REPLAY_WINDOW_HOURS),
            )
            .order_by(SegmentEmission.period_start)
        )
    ).scalars().all()
    hourly_series = [_hourly_point(emission) for emission in replay_rows]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segment": {
            "road_segment_id": segment.road_segment_id, "name": segment.name, "length_km": segment.length_km,
            "activity_class": activity_class,
            "activity_score": primary_hex.skor_total_ahp if primary_hex else None,
            "pollutant_totals": emission.pollutant_totals_g_h if emission else None,
            "data_source": emission.vehicle_count_semantics if emission else None,
            "observed_at": emission.period_end.isoformat() if emission else None,
        },
        "hourly_series": hourly_series,
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
        "stop_assessment": stop_assessment,
        "coverage_gap": coverage_gap,
        "intervention_hint": intervention_hint,
    }
