"""Labeled borrowed estimates for road segments with no observation of their own.

The 54 non-LIVE cameras cover a subset of the road network; the remaining
corridors have no camera and therefore no measured fact. Rather than show them as
empty, the map, the segment panel and Bang Jo borrow the nearest observed
segment's latest static fact and mark it ``data_status = "estimated"`` with the
source segment id, so an estimate is never presented as a measurement.

Borrowing is read-only: it never writes a ``segment_emissions`` row.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.services.emission_analytics import source_mode_expression

# Modes that represent a static, non-live profile.
STATIC_MODES = frozenset({"REPLAY", "SNAPSHOT_REAL"})

OBSERVED = "observed"
ESTIMATED = "estimated"
UNAVAILABLE = "unavailable"


def source_mode_of(emission: SegmentEmission) -> str:
    """Mirror :func:`serialize_model`'s source-mode resolution for one row."""
    metadata = emission.ahp_metadata or {}
    return (
        metadata.get("source_mode")
        or ("SYNTHETIC" if metadata.get("data_source") == "HISTORICAL" else metadata.get("data_source"))
        or "HISTORICAL"
    )


def is_interpolated_of(emission: SegmentEmission) -> bool:
    metadata = (emission.ahp_metadata or {}).get("calculation_metadata") or {}
    return bool(metadata.get("is_interpolated"))


@dataclass(frozen=True, slots=True)
class DisplayFact:
    """One segment's map/panel fact, measured or borrowed."""
    emission: SegmentEmission | None
    data_status: str
    borrowed_from: str | None = None

    @property
    def source_mode(self) -> str | None:
        return source_mode_of(self.emission) if self.emission is not None else None

    @property
    def is_static(self) -> bool:
        return self.source_mode in STATIC_MODES

    @property
    def is_interpolated(self) -> bool:
        return is_interpolated_of(self.emission) if self.emission is not None else False


async def latest_observed_facts(db: AsyncSession) -> dict[str, SegmentEmission]:
    """Newest non-SYNTHETIC fact per road segment that has one."""
    statement = (
        select(RoadSegment.road_segment_id, SegmentEmission)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(source_mode_expression().notin_(["SYNTHETIC"]))
        .distinct(RoadSegment.road_segment_id)
        .order_by(
            RoadSegment.road_segment_id,
            SegmentEmission.period_end.desc(),
            SegmentEmission.calculation_version.desc(),
            SegmentEmission.calculated_at.desc(),
        )
    )
    return {segment_id: emission for segment_id, emission in (await db.execute(statement)).all()}


async def nearest_source_by_segment(
    db: AsyncSession, missing_ids: list[str], source_ids: list[str]
) -> dict[str, str]:
    """Nearest observed segment for each segment without its own fact."""
    if not missing_ids or not source_ids:
        return {}
    target, source = aliased(RoadSegment), aliased(RoadSegment)
    # Correlated scalar subquery (not a cross join) so no cartesian-product
    # warning is emitted and the planner picks one nearest source per target.
    nearest = (
        select(source.road_segment_id)
        .where(source.road_segment_id.in_(source_ids))
        .order_by(func.ST_Distance(target.geometry, source.geometry))
        .limit(1)
        .correlate(target)
        .scalar_subquery()
    )
    statement = select(target.road_segment_id, nearest).where(target.road_segment_id.in_(missing_ids))
    return {target_id: source_id for target_id, source_id in (await db.execute(statement)).all() if source_id is not None}


async def build_display_facts(db: AsyncSession) -> dict[str, DisplayFact]:
    """One fact per road segment: measured where possible, else borrowed."""
    observed = await latest_observed_facts(db)
    all_ids = set((await db.execute(select(RoadSegment.road_segment_id))).scalars().all())
    missing = sorted(all_ids - set(observed))
    nearest = await nearest_source_by_segment(db, missing, sorted(observed))

    facts: dict[str, DisplayFact] = {
        segment_id: DisplayFact(emission=emission, data_status=OBSERVED)
        for segment_id, emission in observed.items()
    }
    for segment_id in missing:
        source_id = nearest.get(segment_id)
        if source_id is None:
            facts[segment_id] = DisplayFact(emission=None, data_status=UNAVAILABLE)
        else:
            facts[segment_id] = DisplayFact(
                emission=observed[source_id], data_status=ESTIMATED, borrowed_from=source_id
            )
    return facts


async def build_display_fact(db: AsyncSession, road_segment_id: str) -> DisplayFact | None:
    """Display fact for one segment, borrowing when it has no own observation."""
    observed = await latest_observed_facts(db)
    emission = observed.get(road_segment_id)
    if emission is not None:
        return DisplayFact(emission=emission, data_status=OBSERVED)
    exists = (
        await db.execute(select(RoadSegment.road_segment_id).where(RoadSegment.road_segment_id == road_segment_id))
    ).first()
    if exists is None:
        return None
    nearest = await nearest_source_by_segment(db, [road_segment_id], list(observed))
    source_id = nearest.get(road_segment_id)
    if source_id is None:
        return DisplayFact(emission=None, data_status=UNAVAILABLE)
    return DisplayFact(emission=observed[source_id], data_status=ESTIMATED, borrowed_from=source_id)
