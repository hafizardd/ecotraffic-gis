"""Populate segment population context independently of traffic observations."""

import logging

from sqlalchemy import select

from app.core.database import get_sync_db
from app.models.road_segment import RoadSegment
from app.services.spatial_integration import compute_population_context

logger = logging.getLogger(__name__)


def backfill() -> dict[str, int]:
    counts = {"total": 0, "completed": 0, "pending": 0, "failed": 0}
    with get_sync_db() as db:
        for segment in db.execute(select(RoadSegment).order_by(RoadSegment.road_segment_id)).scalars():
            counts["total"] += 1
            try:
                population_context = compute_population_context(db, segment)
                segment.spatial_metadata = {**(segment.spatial_metadata or {}), "population_context": population_context}
                primary = (population_context or {}).get("primary")
                segment.population = primary.get("population") if primary else None
                db.commit()
                counts["completed" if population_context else "pending"] += 1
            except Exception:
                logger.exception("backfill_spatial_context_failed", extra={"segment_id": segment.road_segment_id})
                db.rollback()
                counts["failed"] += 1
    print(counts)
    return counts


if __name__ == "__main__":
    backfill()
