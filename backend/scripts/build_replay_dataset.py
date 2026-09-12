"""Build the precomputed hourly REPLAY dataset from real SNAPSHOT_REAL facts.

One-off (idempotent) job: for every road segment with real ``SNAPSHOT_REAL``
segment_emissions in the last 24 UTC hour buckets (ending with the current
hour), average those facts into one ``REPLAY`` SegmentEmission row per hour
bucket. Gaps are filled from the nearest real hours (linear between two real
hours; forward/backward fill at the day edges) and every filled hour is flagged
with ``calculation_metadata.is_interpolated`` so it can never be mistaken for an
observed hour.

The aggregation is the same mean-per-segment-per-bucket semantics
``emission_analytics.segment_means()`` uses, scoped to ``source_mode = "SNAPSHOT_REAL"``
via ``fact_query``. Only ever aggregates from SNAPSHOT_REAL, never from REPLAY,
and upserts on ``uq_segment_emission_period_version`` with a dedicated
``calculation_version`` (3) that cannot collide with LIVE/SNAPSHOT_REAL rows (2).

Timezone: ``period_start`` is stored in UTC and every read path buckets hours on
UTC (``activity_grid._available_hours`` floors the UTC epoch). Buckets are
therefore UTC hour boundaries, not Asia/Jakarta local hours.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import argparse
import logging

from sqlalchemy import Float, cast, func, select

from app.core.database import get_sync_db
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.services.emission_analytics import (
    BUCKETS,
    POLLUTANTS,
    VEHICLE_KEYS,
    AnalyticsFilter,
    fact_query,
    rate,
)
from app.services.segment_emission_store import persist_segment_emission_sync

logger = logging.getLogger(__name__)

SOURCE_MODE = "SNAPSHOT_REAL"
REPLAY_MODE = "REPLAY"
# LIVE/SNAPSHOT_REAL facts use calculation_version 2 (segment_emission_pipeline).
REPLAY_CALCULATION_VERSION = 3
HOUR = timedelta(seconds=BUCKETS["1h"])
WINDOW_HOURS = 24

METRIC_FIELDS = (
    tuple(f"{pollutant.lower()}_kg_h" for pollutant in POLLUTANTS)
    + tuple(f"volume_{key}" for key in VEHICLE_KEYS)
    + tuple(f"vkt_{key}" for key in VEHICLE_KEYS)
    + tuple(f"raw_{key}" for key in VEHICLE_KEYS)
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """24 UTC hour buckets ending with the current hour: ``[start, end)``.

    Ending on the current (possibly partial) hour keeps all 24 buckets within
    ``_available_hours``' ``period_start >= now - 24h`` cutoff, so the map time
    slider exposes a full day.
    """
    end = _as_utc(now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return end - timedelta(hours=WINDOW_HOURS), end


def _segment_filter(segment_id: str, start: datetime, end: datetime) -> AnalyticsFilter:
    # Restricting source_mode is the guard that REPLAY is always derived from
    # SNAPSHOT_REAL only: REPLAY rows can never enter this aggregation.
    return AnalyticsFilter(start, end, segment_id=segment_id, source_mode=SOURCE_MODE)


def _segments_with_snapshot(db, start: datetime, end: datetime) -> list[tuple[str, object]]:
    stmt = (
        select(RoadSegment.road_segment_id, RoadSegment.id)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(
            SegmentEmission.period_start >= start,
            SegmentEmission.period_start < end,
            SegmentEmission.ahp_metadata["source_mode"].astext == SOURCE_MODE,
        )
        .distinct()
    )
    return db.execute(stmt).all()


def _replay_keys(db, start: datetime, end: datetime) -> set[tuple[str, datetime]]:
    stmt = (
        select(RoadSegment.road_segment_id, SegmentEmission.period_start)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(
            SegmentEmission.period_start >= start,
            SegmentEmission.period_start < end,
            SegmentEmission.ahp_metadata["source_mode"].astext == REPLAY_MODE,
        )
        .distinct()
    )
    return {(segment_id, _as_utc(period_start)) for segment_id, period_start in db.execute(stmt).all()}


def _hourly_means(db, segment_id: str, start: datetime, end: datetime) -> dict[datetime, dict]:
    """Mean rate/volume/VKT per UTC hour for one segment's SNAPSHOT_REAL facts.

    Mirrors ``emission_analytics.segment_means`` / ``vehicle_segment_means``
    (mean per segment per bucket) but returns every field the store needs in one
    pass, including the raw snapshot counts.
    """
    facts = fact_query(_segment_filter(segment_id, start, end)).cte("facts")
    hour = func.to_timestamp(
        func.floor(func.extract("epoch", facts.c.period_start) / BUCKETS["1h"]) * BUCKETS["1h"]
    ).label("hour")
    columns = [
        func.avg(rate(facts.c.pollutant_totals_g_h, pollutant)).label(f"{pollutant.lower()}_kg_h")
        for pollutant in POLLUTANTS
    ]
    columns += [
        func.avg(cast(facts.c.volume_per_hour[key].astext, Float)).label(f"volume_{key}")
        for key in VEHICLE_KEYS
    ]
    columns += [
        func.avg(cast(facts.c.vkt_km_h[key].astext, Float)).label(f"vkt_{key}")
        for key in VEHICLE_KEYS
    ]
    columns += [
        func.avg(cast(facts.c.raw_counts[key].astext, Float)).label(f"raw_{key}")
        for key in VEHICLE_KEYS
    ]
    columns += [
        func.count().label("sample_count"),
        func.max(func.coalesce(
            cast(facts.c.ahp_metadata["observed_at"].astext, facts.c.period_end.type),
            facts.c.period_end,
        )).label("observed_at"),
    ]
    stmt = select(hour, *columns).group_by(hour).order_by(hour)
    return {_as_utc(row["hour"]): dict(row) for row in db.execute(stmt).mappings()}


def _gap_plan(present: list[bool]) -> list[tuple[str, int | None, int | None] | None]:
    """Per-bucket fill rule: None = real sample, else (method, left, right)."""
    real = [index for index, has_value in enumerate(present) if has_value]
    plan: list[tuple[str, int | None, int | None] | None] = [None] * len(present)
    if not real:
        return plan
    for index, has_value in enumerate(present):
        if has_value:
            continue
        left = max((candidate for candidate in real if candidate < index), default=None)
        right = min((candidate for candidate in real if candidate > index), default=None)
        if left is not None and right is not None:
            plan[index] = ("linear", left, right)
        elif left is not None:
            plan[index] = ("forward_fill", left, None)
        else:
            plan[index] = ("backward_fill", None, right)
    return plan


def _fill_value(values: list[float | None], plan, index: int) -> float | None:
    method, left, right = plan
    if method == "linear":
        left_value = values[left] if left is not None else None
        right_value = values[right] if right is not None else None
        if left_value is None:
            return right_value
        if right_value is None:
            return left_value
        return left_value + (right_value - left_value) * (index - left) / (right - left)
    source = values[left] if method == "forward_fill" else values[right]
    return source


def _filled_series(means: dict[datetime, dict], buckets: list[datetime], plan) -> dict[str, list[float | None]]:
    series: dict[str, list[float | None]] = {}
    for field in METRIC_FIELDS:
        values = [means[bucket].get(field) if bucket in means else None for bucket in buckets]
        series[field] = [
            value if plan[index] is None else _fill_value(values, plan[index], index)
            for index, value in enumerate(values)
        ]
    return series


def _source_hours(buckets: list[datetime], plan) -> list[str]:
    _, left, right = plan
    indices = [index for index in (left, right) if index is not None]
    return [buckets[index].isoformat() for index in indices]


def _replay_result(segment, bucket: datetime, values: dict, *, plan, sample_count: int,
                   observed_at, interpolated_from: list[str] | None = None) -> dict:
    hour_end = bucket + HOUR
    is_interpolated = plan is not None
    method = plan[0] if plan is not None else None
    totals_g_h = {}
    for pollutant in POLLUTANTS:
        value = values.get(f"{pollutant.lower()}_kg_h")
        totals_g_h[pollutant] = value * 1000 if value is not None else None
    observed = observed_at or hour_end
    return {
        "period_start": bucket,
        "period_end": hour_end,
        "calculated_at": datetime.now(timezone.utc),
        "calculation_version": REPLAY_CALCULATION_VERSION,
        "calculation_mode": "replay_hourly_mean",
        "observation_duration_seconds": float(BUCKETS["1h"]),
        "data_source": "HISTORICAL",
        "source_mode": REPLAY_MODE,
        "observed_at": observed.isoformat() if isinstance(observed, datetime) else str(observed),
        "vehicle_count_semantics": "snapshot_occupancy",
        "raw_counts": {key: values.get(f"raw_{key}") for key in VEHICLE_KEYS},
        "volume_per_hour": {key: values.get(f"volume_{key}") for key in VEHICLE_KEYS},
        "vkt_km_h": {key: values.get(f"vkt_{key}") for key in VEHICLE_KEYS},
        "emissions": {"totals_g_h": totals_g_h, "by_category_g_h": {}},
        "calculation_metadata": {
            "is_interpolated": is_interpolated,
            "interpolation_method": method,
            "interpolated_from": interpolated_from or [],
            "replay_source_mode": SOURCE_MODE,
            "replay_bucket_seconds": BUCKETS["1h"],
            "replay_timezone": "UTC",
            "source_sample_count": sample_count,
        },
        "provenance": {
            "source_cameras": [],
            "source_streams": [],
            "source_observation_count": sample_count,
            "aggregation_policy": "sum_independent_streams",
        },
    }


def build(only_missing: bool = False, now: datetime | None = None) -> int:
    start, end = _window(now)
    buckets = [start + index * HOUR for index in range(WINDOW_HOURS)]
    created = 0
    with get_sync_db() as db:
        segments = _segments_with_snapshot(db, start, end)
        existing = _replay_keys(db, start, end) if only_missing else set()
        for segment_id, segment_database_id in segments:
            segment = db.execute(
                select(RoadSegment).where(RoadSegment.id == segment_database_id)
            ).scalar_one()
            means = _hourly_means(db, segment_id, start, end)
            if not means:
                logger.info("replay_segment_skipped_no_real_samples", extra={"segment_id": segment_id})
                continue
            plan = _gap_plan([bucket in means for bucket in buckets])
            series = _filled_series(means, buckets, plan)
            for index, bucket in enumerate(buckets):
                if (segment_id, bucket) in existing:
                    continue
                row = dict(means.get(bucket) or {})
                values = {field: series[field][index] for field in METRIC_FIELDS}
                real = plan[index] is None
                result = _replay_result(
                    segment,
                    bucket,
                    values,
                    plan=plan[index],
                    sample_count=int(row.get("sample_count") or 0) if real else 0,
                    observed_at=row.get("observed_at") if real else None,
                    interpolated_from=None if real else _source_hours(buckets, plan[index]),
                )
                persist_segment_emission_sync(db, segment_database_id, result)
                created += 1
            db.commit()
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-missing", action="store_true",
                        help="Only write segment-hour buckets that have no REPLAY row yet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(f"Wrote {build(only_missing=args.only_missing)} REPLAY hourly segment records")
