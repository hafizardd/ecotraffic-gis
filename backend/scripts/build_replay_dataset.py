"""Build the precomputed hourly REPLAY dataset from the durable snapshot facts.

One-off (idempotent) job: for every road segment with real snapshot-derived
``segment_emissions`` facts over the last 24 UTC hour buckets (ending with the
latest collected hour), average those facts into one ``REPLAY`` SegmentEmission
row per hour bucket. Gaps are filled from the nearest real hours (linear between
two real hours; forward/backward fill at the day edges) and every filled hour is
flagged with ``calculation_metadata.is_interpolated`` so it can never be mistaken
for an observed hour.

The source is the version-2 ``segment_emissions`` written by the snapshot
reconciler from the non-LIVE cameras' ``snapshot_occupancy`` observations. Those
rows used to be overwritten when the LIVE reconciler shared calculation_version
2; the snapshot writer now versions its facts separately, so this builder can
always re-derive the static profile from what was actually collected. It never
aggregates its own REPLAY outputs.

The profile is anchored to the latest collected source fact rather than
``now()``: the 54 non-LIVE cameras are a completed, static 24-hour collection, so
the same profile stays addressable on any calendar day (the activity-grid and
history lenses map a requested day onto these buckets).

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
from app.services.emission_analytics import BUCKETS, POLLUTANTS, VEHICLE_KEYS
from app.services.segment_emission_store import persist_segment_emission_sync

logger = logging.getLogger(__name__)

# Snapshot facts come from the reconciler (version 2) tagged snapshot_occupancy.
SOURCE_CALCULATION_VERSION = 2
SOURCE_SEMANTICS = "snapshot_occupancy"
REPLAY_MODE = "REPLAY"
# The precomputed static profile gets its own version so it can never collide
# with LIVE (2) or a future SNAPSHOT_REAL (4) fact on the same period.
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


def _window(db) -> tuple[datetime, datetime]:
    """24 UTC hour buckets ending with the latest collected source hour.

    ``[start, end)`` is anchored to the newest snapshot fact, not ``now()``, so a
    finished collection stays addressable no matter when this runs.
    """
    latest = db.execute(
        select(func.max(SegmentEmission.period_start)).where(
            SegmentEmission.calculation_version == SOURCE_CALCULATION_VERSION,
            SegmentEmission.vehicle_count_semantics == SOURCE_SEMANTICS,
        )
    ).scalar_one_or_none()
    anchor = _as_utc(latest) if latest is not None else _as_utc(datetime.now(timezone.utc))
    end = anchor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return end - timedelta(hours=WINDOW_HOURS), end


def _segments_with_source(db, start: datetime, end: datetime) -> list[tuple[str, object]]:
    stmt = (
        select(RoadSegment.road_segment_id, RoadSegment.id)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(
            SegmentEmission.period_start >= start,
            SegmentEmission.period_start < end,
            SegmentEmission.calculation_version == SOURCE_CALCULATION_VERSION,
            SegmentEmission.vehicle_count_semantics == SOURCE_SEMANTICS,
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


def _source_facts(db, segment_database_id, start: datetime, end: datetime):
    """The durable snapshot facts feeding one segment's hourly means."""
    return (
        select(
            SegmentEmission.period_start,
            SegmentEmission.period_end,
            SegmentEmission.pollutant_totals_g_h,
            SegmentEmission.volume_per_hour,
            SegmentEmission.vkt_km_h,
            SegmentEmission.raw_counts,
            SegmentEmission.ahp_metadata,
        )
        .where(
            SegmentEmission.road_segment_id == segment_database_id,
            SegmentEmission.period_start >= start,
            SegmentEmission.period_start < end,
            SegmentEmission.calculation_version == SOURCE_CALCULATION_VERSION,
            SegmentEmission.vehicle_count_semantics == SOURCE_SEMANTICS,
        )
        .cte("facts")
    )


def _hourly_means(db, segment_database_id, start: datetime, end: datetime) -> dict[datetime, dict]:
    """Mean rate/volume/VKT per UTC hour for one segment's snapshot facts.

    Mirrors ``emission_analytics.segment_means`` / ``vehicle_segment_means``
    (mean per segment per bucket) but returns every field the store needs in one
    pass, including the raw snapshot counts.
    """
    facts = _source_facts(db, segment_database_id, start, end)
    hour = func.to_timestamp(
        func.floor(func.extract("epoch", facts.c.period_start) / BUCKETS["1h"]) * BUCKETS["1h"]
    ).label("hour")
    columns = [
        func.avg(cast(facts.c.pollutant_totals_g_h[pollutant].astext, Float) / 1000.0).label(f"{pollutant.lower()}_kg_h")
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
            "replay_source": "snapshot_occupancy",
            "replay_source_version": SOURCE_CALCULATION_VERSION,
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
    created = 0
    with get_sync_db() as db:
        start, end = _window(db) if now is None else _fixed_window(now)
        buckets = [start + index * HOUR for index in range(WINDOW_HOURS)]
        segments = _segments_with_source(db, start, end)
        existing = _replay_keys(db, start, end) if only_missing else set()
        for segment_id, segment_database_id in segments:
            means = _hourly_means(db, segment_database_id, start, end)
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
                    segment_id,
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


def _fixed_window(now: datetime) -> tuple[datetime, datetime]:
    end = _as_utc(now).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return end - timedelta(hours=WINDOW_HOURS), end


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-missing", action="store_true",
                        help="Only write segment-hour buckets that have no REPLAY row yet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(f"Wrote {build(only_missing=args.only_missing)} REPLAY hourly segment records")
