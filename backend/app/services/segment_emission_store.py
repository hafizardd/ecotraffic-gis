"""Persistence adapter for calculated segment emissions."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment_emission import SegmentEmission


def _values(segment_database_id: uuid.UUID, result: dict) -> dict:
    provenance = result.get("provenance", {})
    return {
        "road_segment_id": segment_database_id,
        "period_start": result["period_start"],
        "period_end": result["period_end"],
        "calculated_at": result["calculated_at"],
        "calculation_version": result.get("calculation_version", 1),
        "observation_duration_seconds": result["observation_duration_seconds"],
        "aggregation_policy": provenance.get("aggregation_policy", "sum_independent_streams"),
        "source_cameras": list(provenance.get("source_cameras", [])),
        "source_streams": list(provenance.get("source_streams", [])),
        "source_observation_count": provenance.get("source_observation_count", result.get("source_observation_count", len(provenance.get("source_cameras", [])))),
        "vehicle_count_semantics": result.get("vehicle_count_semantics", "unknown"),
        "raw_counts": result["raw_counts"],
        "volume_per_hour": result["volume_per_hour"],
        "vkt_km_h": result["vkt_km_h"],
        "pollutant_totals_g_h": result["emissions"]["totals_g_h"],
        "category_pollutant_breakdown_g_h": result["emissions"].get("by_category_g_h", result["emissions"].get("by_category", {})),
        "raw_criteria": result["raw_criteria"],
        "normalized_criteria": result.get("normalized_criteria"),
        "decision_score": result.get("decision_score"),
        "priority": result.get("priority"),
        "spatial_criteria_status": result.get("spatial_criteria_status", "pending"),
        "ahp_metadata": {
            "weights": result.get("ahp_weights"),
            "consistency": result.get("ahp_consistency"),
            "data_source": result.get("data_source"),
        },
    }


async def persist_segment_emission(
    db: AsyncSession, segment_database_id: uuid.UUID, result: dict
) -> SegmentEmission:
    values = _values(segment_database_id, result)
    existing = (await db.execute(
        select(SegmentEmission).where(
            SegmentEmission.road_segment_id == segment_database_id,
            SegmentEmission.period_start == values["period_start"],
            SegmentEmission.calculation_version == values["calculation_version"],
        )
    )).scalar_one_or_none()
    if existing is None:
        existing = SegmentEmission(**values)
        db.add(existing)
    else:
        for key, value in values.items():
            if key != "road_segment_id":
                setattr(existing, key, value)
    await db.flush()
    return existing


def persist_segment_emission_sync(db, segment_database_id: uuid.UUID, result: dict) -> SegmentEmission:
    values = _values(segment_database_id, result)
    existing = db.execute(
        select(SegmentEmission).where(
            SegmentEmission.road_segment_id == segment_database_id,
            SegmentEmission.period_start == values["period_start"],
            SegmentEmission.calculation_version == values["calculation_version"],
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = SegmentEmission(**values)
        db.add(existing)
    else:
        for key, value in values.items():
            if key != "road_segment_id":
                setattr(existing, key, value)
    db.flush()
    return existing
