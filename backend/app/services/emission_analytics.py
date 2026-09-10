"""Analytics over versioned SegmentEmission facts; all rate aggregation is SQL.

Temporal samples are averaged per segment, then independent segment rates for
the SAME pollutant are summed. No camera estimates or synthetic backfills are
silently mixed into observed segment analytics.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Float, cast, func, select

from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from cv.proposal_emission_factors import POLLUTANTS, VEHICLE_CATEGORIES


BUCKETS = {"1m": 60, "5m": 300, "10m": 600, "15m": 900, "30m": 1800, "1h": 3600}
UNITS = {"emissions": "kg/hour", "volume_per_hour": "vehicles/hour", "vkt_km_h": "km/hour"}


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must include a timezone")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class AnalyticsFilter:
    start: datetime
    end: datetime
    segment_id: str | None = None
    corridor_id: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "start", utc(self.start))
        object.__setattr__(self, "end", utc(self.end))
        if self.start >= self.end:
            raise ValueError("from must be earlier than to")
        if self.end - self.start > timedelta(days=31):
            raise ValueError("Maximum date range is 31 days")

    def bucket(self, requested: str | None = None) -> tuple[str, int]:
        hours = (self.end - self.start).total_seconds() / 3600
        name = requested or ("1m" if hours <= 1 else "5m" if hours <= 3 else "15m" if hours <= 12 else "1h")
        if name not in BUCKETS:
            raise ValueError("bucket must be one of: " + ", ".join(BUCKETS))
        if (self.end - self.start).total_seconds() / BUCKETS[name] > 2000:
            raise ValueError("Too many time buckets; choose a larger bucket")
        return name, BUCKETS[name]


def corridor_columns():
    return (
        func.coalesce(RoadSegment.spatial_metadata["corridor_id"].astext, RoadSegment.road_segment_id),
        func.coalesce(RoadSegment.spatial_metadata["corridor_name"].astext, RoadSegment.name),
    )


def source_mode_expression():
    from sqlalchemy import case
    metadata = SegmentEmission.ahp_metadata
    # All legacy data_source=HISTORICAL rows came from the repository's random
    # backfill generator. Explicit source_mode wins for future real imports.
    return func.coalesce(metadata["source_mode"].astext, case(
        (metadata["data_source"].astext == "HISTORICAL", "SYNTHETIC"),
        else_=metadata["data_source"].astext,
    ), "HISTORICAL")


def fact_query(filters: AnalyticsFilter, *, latest: bool = False):
    corridor_id, corridor_name = corridor_columns()
    stmt = select(
        SegmentEmission,
        RoadSegment.road_segment_id.label("segment_id"),
        RoadSegment.name.label("segment_name"),
        corridor_id.label("corridor_id"), corridor_name.label("corridor_name"),
        source_mode_expression().label("source_mode"),
    ).join(RoadSegment, SegmentEmission.road_segment_id == RoadSegment.id)
    stmt = stmt.where(source_mode_expression().notin_(["SYNTHETIC", "REPLAY"]))
    if filters.segment_id:
        stmt = stmt.where(RoadSegment.road_segment_id == filters.segment_id)
    if filters.corridor_id:
        stmt = stmt.where(corridor_id == filters.corridor_id)
    if latest:
        from app.models.camera_road_segment import CameraRoadSegment
        from app.models.camera import Camera
        stmt = stmt.where(RoadSegment.id.in_(select(CameraRoadSegment.road_segment_id)
            .join(Camera, Camera.id == CameraRoadSegment.camera_id)
            .where(CameraRoadSegment.is_active.is_(True), Camera.is_active.is_(True))))
        return stmt.distinct(SegmentEmission.road_segment_id).order_by(
            SegmentEmission.road_segment_id, SegmentEmission.period_end.desc(),
            SegmentEmission.calculation_version.desc(), SegmentEmission.calculated_at.desc())
    stmt = stmt.where(SegmentEmission.period_start >= filters.start, SegmentEmission.period_start < filters.end)
    # A recalculation replaces an analytical sample, it does not add another one.
    return stmt.distinct(SegmentEmission.road_segment_id, SegmentEmission.period_start).order_by(
        SegmentEmission.road_segment_id, SegmentEmission.period_start,
        SegmentEmission.calculation_version.desc(), SegmentEmission.calculated_at.desc())


def rate(column, pollutant: str):
    # Missing old pollutant values stay null; absence must never become zero.
    return cast(column[pollutant].astext, Float) / 1000.0


def segment_means(filters: AnalyticsFilter, bucket_seconds: int | None = None):
    facts = fact_query(filters).cte("facts")
    keys = [facts.c.segment_id, facts.c.segment_name, facts.c.corridor_id, facts.c.corridor_name]
    if bucket_seconds:
        keys.insert(0, func.to_timestamp(func.floor(func.extract("epoch", facts.c.period_start) / bucket_seconds) * bucket_seconds).label("timestamp"))
    return select(*keys,
        *[func.avg(rate(facts.c.pollutant_totals_g_h, p)).label(f"{p.lower()}_kg_h") for p in POLLUTANTS],
        func.count().label("sample_count"), func.max(func.coalesce(
            cast(facts.c.ahp_metadata["observed_at"].astext, facts.c.period_end.type), facts.c.period_end)).label("observed_at"),
        func.count().filter(facts.c.vehicle_count_semantics == "snapshot_occupancy").label("estimated_sample_count"),
    ).group_by(*keys).cte("segment_means")


def trend_query(filters: AnalyticsFilter, seconds: int):
    means = segment_means(filters, seconds)
    return select(means.c.timestamp,
        *[func.sum(means.c[f"{p.lower()}_kg_h"]).label(f"{p.lower()}_kg_h") for p in POLLUTANTS],
        func.count().label("segment_count"), func.sum(means.c.sample_count).label("sample_count"),
        func.sum(means.c.estimated_sample_count).label("estimated_sample_count"),
    ).group_by(means.c.timestamp).order_by(means.c.timestamp)


def top_query(filters: AnalyticsFilter, limit: int, pollutant: str = "co2"):
    means = segment_means(filters)
    value = func.sum(means.c[f"{pollutant}_kg_h"]).label("emission_kg_h")
    return select(means.c.corridor_id, means.c.corridor_name, value,
        func.array_agg(means.c.segment_id).label("segment_ids"),
        func.sum(means.c.sample_count).label("sample_count"),
        func.sum(means.c.estimated_sample_count).label("estimated_sample_count"),
        func.max(means.c.observed_at).label("observed_at"),
    ).group_by(means.c.corridor_id, means.c.corridor_name).order_by(value.desc().nullslast(), means.c.corridor_id).limit(limit)


def composition_query(filters: AnalyticsFilter):
    means = segment_means(filters)
    return select(*[func.sum(means.c[f"{p.lower()}_kg_h"]).label(p) for p in POLLUTANTS],
        func.sum(means.c.sample_count).label("sample_count"),
        func.sum(means.c.estimated_sample_count).label("estimated_sample_count"))


def history_query(filters: AnalyticsFilter):
    facts = fact_query(filters).cte("facts")
    return select(facts).order_by(facts.c.period_start.desc(), facts.c.segment_id)


def serialize_fact(row, now: datetime | None = None) -> dict:
    """One serializer for REST, exports, Redis and WebSocket segment facts."""
    now = now or datetime.now(timezone.utc)
    metadata = row["ahp_metadata"] or {}
    observed = metadata.get("observed_at") or row["period_end"]
    if isinstance(observed, str):
        observed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    age = max(0, (now - utc(observed)).total_seconds())
    estimated = row["vehicle_count_semantics"] == "snapshot_occupancy"
    from app.core.config import settings
    stale_after = max(settings.DATA_AGING_THRESHOLD_SECONDS, settings.SEGMENT_OBSERVATION_WINDOW_SECONDS * 3)
    totals = row["pollutant_totals_g_h"] or {}
    def iso(value):
        return value.isoformat() if isinstance(value, datetime) else value
    return {
        "id": str(row["id"]), "segment_id": row["segment_id"], "segment_name": row["segment_name"],
        "corridor_id": row["corridor_id"], "corridor_name": row["corridor_name"],
        "period_start": iso(row["period_start"]), "period_end": iso(row["period_end"]),
        "observed_at": iso(observed), "processed_at": iso(row["calculated_at"]),
        "calculation_version": row["calculation_version"], "source_mode": row["source_mode"],
        "vehicle_count_semantics": row["vehicle_count_semantics"],
        "calculation_mode": metadata.get("calculation_mode") or ("live_occupancy_estimate" if estimated else "flow_based_segment"),
        "quality_status": "estimated" if estimated else "observed",
        "freshness_seconds": age, "stale_after_seconds": stale_after,
        "freshness_status": "fresh" if age <= stale_after else "stale",
        "emissions_kg_h": {p.lower(): float(totals[p]) / 1000 if p in totals else None for p in POLLUTANTS},
        "volume_per_hour": row["volume_per_hour"], "vkt_km_h": row["vkt_km_h"],
        "raw_counts": row["raw_counts"], "source_cameras": row["source_cameras"],
        "source_streams": row["source_streams"], "source_observation_count": row["source_observation_count"],
        "observation_duration_seconds": row["observation_duration_seconds"],
        "aggregation_policy": row["aggregation_policy"],
        "category_pollutant_breakdown_g_h": row["category_pollutant_breakdown_g_h"],
        "calculation_metadata": metadata.get("calculation_metadata", {}), "units": UNITS,
    }


def serialize_model(segment, emission):
    spatial = segment.spatial_metadata or {}
    metadata = emission.ahp_metadata or {}
    row = {column.name: getattr(emission, column.name) for column in SegmentEmission.__table__.columns}
    row.update(segment_id=segment.road_segment_id, segment_name=segment.name,
        corridor_id=spatial.get("corridor_id") or segment.road_segment_id,
        corridor_name=spatial.get("corridor_name") or segment.name,
        source_mode=metadata.get("source_mode") or ("SYNTHETIC" if metadata.get("data_source") == "HISTORICAL" else metadata.get("data_source")) or "HISTORICAL")
    return serialize_fact(row)


EXPORT_FIELDS = ["segment_id", "segment_name", "corridor_id", "corridor_name", "period_start", "period_end",
    "source_mode", "vehicle_count_semantics", "calculation_mode", "quality_status",
    *[f"{p.lower()}_kg_h" for p in POLLUTANTS],
    *[f"{c}_vehicles_h" for c in VEHICLE_CATEGORIES], *[f"{c}_vkt_km_h" for c in VEHICLE_CATEGORIES],
    "observed_at", "processed_at", "calculation_version", "source_cameras", "source_streams",
    "source_observation_count", "observation_duration_seconds", "calculation_metadata"]


def export_row(record: dict):
    import json
    values = {key: record.get(key) for key in EXPORT_FIELDS}
    values.update({f"{p}_kg_h": v for p, v in record["emissions_kg_h"].items()})
    for category in VEHICLE_CATEGORIES:
        values[f"{category}_vehicles_h"] = (record["volume_per_hour"] or {}).get(category)
        values[f"{category}_vkt_km_h"] = (record["vkt_km_h"] or {}).get(category)
    for key, value in values.items():
        if isinstance(value, (dict, list)):
            values[key] = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
            values[key] = "'" + value
    return values
