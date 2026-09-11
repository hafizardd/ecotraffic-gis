"""Segment emission analytics and exports with one shared filter contract."""

from datetime import datetime, timedelta, timezone
import csv
import json
import logging
from tempfile import SpooledTemporaryFile
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from starlette.background import BackgroundTask

from app.core.config import settings
from app.core.database import get_db
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.services.emission_analytics import (
    AnalyticsFilter, EXPORT_FIELDS, HISTORY_SORTS, POLLUTANTS, UNITS, VEHICLE_KEYS, composition_query,
    corridor_columns, export_row, fact_query, history_id_query, history_query, serialize_fact,
    serialize_history, top_query, trend_query, vehicle_composition, vehicle_ranking_query,
    vehicle_series_query, vehicle_totals_query,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics/emissions", tags=["emission-analytics"])

_DELETE_BATCH_SIZE = 2000
_DELETE_MAX = 100_000


async def analytics_db():
    try:
        async for db in get_db():
            yield db
    except SQLAlchemyError as exc:
        logger.exception("emission_analytics_database_unavailable")
        raise HTTPException(503, "Emission analytics database unavailable") from exc


async def get_filters(
    from_: datetime | None = Query(None, alias="from"), to: datetime | None = Query(None),
    segment_id: str | None = Query(None, max_length=100), corridor_id: str | None = Query(None, max_length=255),
    search: str | None = Query(None, max_length=100),
    quality_status: Literal["observed", "estimated"] | None = Query(None),
    source_mode: str | None = Query(None, max_length=40),
    db=Depends(analytics_db),
):
    end = to or datetime.now(timezone.utc)
    try:
        filters = AnalyticsFilter(from_ or end - timedelta(hours=24), end, segment_id, corridor_id,
            search, quality_status, source_mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if segment_id and not (await db.execute(select(RoadSegment.id).where(RoadSegment.road_segment_id == segment_id).limit(1))).first():
        raise HTTPException(404, "Segment not found")
    if corridor_id and not (await db.execute(select(RoadSegment.id).where(corridor_columns()[0] == corridor_id).limit(1))).first():
        raise HTTPException(404, "Corridor not found")
    return filters


def envelope(filters: AnalyticsFilter):
    return {"from": filters.start, "to": filters.end, "segment_id": filters.segment_id,
        "corridor_id": filters.corridor_id, "search": filters.search,
        "quality_status": filters.quality_status, "source_mode": filters.source_mode, "units": UNITS,
        "aggregation": "mean_per_segment_then_sum_independent_segments",
        # SNAPSHOT_REAL is intentionally NOT excluded: it is real sampled data.
        "excluded_source_modes": ["SYNTHETIC", "REPLAY"]}


@router.get("/options")
async def options(db=Depends(analytics_db)):
    corridor_id, corridor_name = corridor_columns()
    rows = (await db.execute(select(RoadSegment.road_segment_id.label("segment_id"),
        RoadSegment.name.label("segment_name"), corridor_id.label("corridor_id"),
        corridor_name.label("corridor_name")).order_by(RoadSegment.name))).mappings().all()
    return {"segments": [dict(row) for row in rows]}


@router.get("/latest")
async def latest(filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    now = datetime.now(timezone.utc)
    facts = fact_query(filters, latest=True).cte("latest_facts")
    rows = (await db.execute(select(facts))).mappings().all()
    segments = [serialize_fact(row, now) for row in rows]
    # Bounded by active segments, never historical sample count. Compute the
    # spatial rollup here so React only displays backend rates.
    totals = {p.lower(): (sum(s["emissions_kg_h"][p.lower()] for s in segments)
        if segments and all(s["emissions_kg_h"][p.lower()] is not None for s in segments) else None) for p in POLLUTANTS}
    oldest = min((s["observed_at"] for s in segments), default=None)
    return {"timestamp": now, "segments": segments, "units": UNITS,
        "summary": {"emissions_kg_h": totals, "segment_count": len(segments),
            "estimated_segment_count": sum(s["quality_status"] == "estimated" for s in segments),
            "freshness_seconds": max((s["freshness_seconds"] for s in segments), default=None),
            "stale_after_seconds": min((s["stale_after_seconds"] for s in segments), default=180),
            "observed_at": oldest,
            "processed_at": max((s["processed_at"] for s in segments), default=None),
            "source_mode": "LIVE" if segments and all(s["source_mode"] == "LIVE" for s in segments) else "HISTORICAL",
        }}


@router.get("/trend")
async def trend(bucket: str | None = Query(None), filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    try:
        name, seconds = filters.bucket(bucket)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    rows = (await db.execute(trend_query(filters, seconds))).mappings().all()
    return {**envelope(filters), "bucket": name, "data": [dict(row) for row in rows]}


@router.get("/top-corridors")
async def top_corridors(limit: int = Query(5, ge=1, le=50),
    pollutant: Literal["tsp", "co", "nox", "so2", "hc", "co2", "ch4", "n2o"] = "co2",
    filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    rows = (await db.execute(top_query(filters, limit, pollutant))).mappings().all()
    return {**envelope(filters), "pollutant": pollutant, "data": [
        {"rank": rank, **dict(row), "pollutant": pollutant} for rank, row in enumerate(rows, 1)]}


@router.get("/composition")
async def composition(filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    row = (await db.execute(composition_query(filters))).mappings().one()
    return {**envelope(filters), "sample_count": row["sample_count"] or 0,
        "estimated_sample_count": row["estimated_sample_count"] or 0,
        "data": [{"pollutant": p, "key": p.lower(), "kg_h": row[p]} for p in POLLUTANTS]}


@router.get("/vehicles")
async def vehicles(ranking_limit: int = Query(8, ge=1, le=50), bucket: str | None = Query(None),
    filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    try:
        name, seconds = filters.bucket(bucket)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    totals = (await db.execute(vehicle_totals_query(filters))).mappings().one()
    ranking = (await db.execute(vehicle_ranking_query(filters, ranking_limit))).mappings().all()
    series = (await db.execute(vehicle_series_query(filters, seconds))).mappings().all()
    volume = {key: totals[f"{key}_veh_h"] for key in VEHICLE_KEYS}
    vkt = {key: totals[f"{key}_vkt"] for key in VEHICLE_KEYS}
    present = any(value is not None for value in volume.values())
    vkt_present = any(value is not None for value in vkt.values())
    return {**envelope(filters), "bucket": name,
        "units": {"volume_per_hour": "vehicles/hour", "vkt_km_h": "km/hour"},
        "totals": volume,
        "total_vehicles_per_hour": sum(value for value in volume.values() if value is not None) if present else None,
        "vkt": vkt,
        "total_vkt_km_h": sum(value for value in vkt.values() if value is not None) if vkt_present else None,
        "composition": vehicle_composition(volume),
        "ranking": [{"rank": rank, **dict(row)} for rank, row in enumerate(ranking, 1)],
        "series": [dict(row) for row in series],
        "sample_count": totals["sample_count"] or 0,
        "estimated_sample_count": totals["estimated_sample_count"] or 0}


@router.get("/history")
async def history(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    sort: str = Query("period_start"), order: Literal["asc", "desc"] = "desc",
    filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    if sort not in HISTORY_SORTS:
        raise HTTPException(422, "sort must be one of: " + ", ".join(HISTORY_SORTS))
    query = history_query(filters, sort, order)
    total = (await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))).scalar_one()
    rows = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).mappings().all()
    return {**envelope(filters), "page": page, "page_size": page_size, "total": total,
        "sort": sort, "order": order, "data": [serialize_history(row) for row in rows]}


def _chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


async def _evict_segment_latest_states(segment_ids):
    """Best-effort Redis eviction so the map cannot keep showing deleted rows."""
    if not segment_ids:
        return
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        try:
            await client.delete(*[f"emission:segment:{segment_id}" for segment_id in segment_ids])
        finally:
            await client.aclose()
    except Exception:
        logger.warning("emission_history_redis_eviction_failed", exc_info=True)


@router.delete("/history")
async def delete_history(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    sort: str = Query("period_start"), order: Literal["asc", "desc"] = "desc",
    scope: Literal["beyond", "page"] = "beyond", dry_run: bool = False,
    filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    if sort not in HISTORY_SORTS:
        raise HTTPException(422, "sort must be one of: " + ", ".join(HISTORY_SORTS))
    query = history_id_query(filters, sort, order)
    total = (await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))).scalar_one()
    # `beyond` keeps pages 1..N and deletes from page N+1; `page` deletes page N only.
    offset = page * page_size if scope == "beyond" else (page - 1) * page_size
    matched = max(0, total - offset) if scope == "beyond" else max(0, min(page_size, total - offset))
    if dry_run:
        return {"matched": matched, "truncated": scope == "beyond" and matched > _DELETE_MAX}

    # Same ordered facts the history table shows, so deletes stay on-screen.
    statement = query.offset(offset)
    if scope == "beyond":
        statement = statement.limit(_DELETE_MAX + 1)
    else:
        statement = statement.limit(page_size)
    rows = (await db.execute(statement)).all()
    truncated = len(rows) > _DELETE_MAX
    ids = [row[0] for row in rows[:_DELETE_MAX]]
    segment_ids = {row[1] for row in rows[:_DELETE_MAX]}
    deleted = 0
    for batch in _chunks(ids, _DELETE_BATCH_SIZE):
        result = await db.execute(delete(SegmentEmission).where(SegmentEmission.id.in_(batch)))
        deleted += result.rowcount or 0
    await db.commit()
    await _evict_segment_latest_states(segment_ids)
    return {"deleted": deleted, "truncated": truncated}


@router.get("/export")
async def export(format: Literal["csv", "json"] = "csv",
    filters: AnalyticsFilter = Depends(get_filters), db=Depends(analytics_db)):
    # Spool while the request's DB dependency is open. FastAPI versions that
    # close yielded dependencies before streaming must not close our cursor.
    output = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+", encoding="utf-8", newline="")
    try:
        query = history_query(filters)
        total = (await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))).scalar_one()
        if total > 100_000:
            raise HTTPException(413, "Export exceeds 100000 records; narrow the date range or segment filter")
        stream = await db.stream(query.execution_options(yield_per=500))
        try:
            if format == "csv":
                output.write("\ufeff")
                writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS)
                writer.writeheader()
            else:
                output.write('{"metadata":' + json.dumps(envelope(filters), default=str) + ',"data":[')
            first = True
            async for row in stream.mappings():
                record = serialize_fact(row)
                if format == "csv":
                    writer.writerow(export_row(record))
                else:
                    if not first:
                        output.write(",")
                    output.write(json.dumps(record, ensure_ascii=False))
                first = False
            if format == "json":
                output.write("]}")
        finally:
            await stream.close()
        output.seek(0)
    except BaseException:
        output.close()
        raise
    return StreamingResponse(iter(lambda: output.read(64 * 1024), ""),
        media_type="text/csv" if format == "csv" else "application/json",
        headers={"Content-Disposition": f'attachment; filename="emission-history.{format}"'},
        background=BackgroundTask(output.close))
