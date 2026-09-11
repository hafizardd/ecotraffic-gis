"""Live hourly re-scoring of the activity-potential hex grid.

Only the volume input is recomputed from live ``segment_emissions`` rows; the
offline ``norm_poi``/``norm_penduduk`` and the fixed AHP weights are reused
as-is. A hex with no mapped segment (or no volume sample) in the hour keeps a
``None`` score rather than a fabricated zero, mirroring the pipeline norm that
missing spatial data is omitted, never invented.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.services.classification import quintile_classify
from app.services.emission_analytics import (
    BUCKETS,
    VEHICLE_KEYS,
    AnalyticsFilter,
    vehicle_segment_means,
)

# From the 'AHP Bobot' Saaty matrix (CR = 0.0096). Same values the offline
# importer verifies against; kept here as the single source of truth so the
# live recomputation can never drift from the stored snapshot.
HEX_AHP_WEIGHTS = {"volume": 0.5390, "poi": 0.2973, "penduduk": 0.1638}

NO_DATA = {"norm_volume": None, "skor_total_ahp": None, "ranking": None,
           "klasifikasi_potensi": None, "data_status": "no_data"}

# Coarse LOD is a presentation approximation: fixed cells are unioned into
# larger super-cells and colored by the area-weighted mean of their member
# tiers. It is not an independently scored cell, so hex_id stays null.
POTENTIAL_LABELS = {1: "Sangat Rendah", 2: "Rendah", 3: "Sedang", 4: "Tinggi", 5: "Sangat Tinggi"}


def label_potential(label: str | None) -> int:
    """Mirror of the frontend ``classificationTier`` label->1..5 mapping (5 highest)."""
    value = (label or "").lower()
    if not value:
        return 0
    if "sangat tinggi" in value or "merah" in value:
        return 5
    if "sangat rendah" in value or "hijau muda" in value:
        return 1
    if "tinggi" in value or "oranye" in value or "orange" in value:
        return 4
    if "sedang" in value or "kuning" in value:
        return 3
    if "rendah" in value or "hijau" in value:
        return 2
    return 0


def aggregate_potential(members: list[tuple[str | None, float]]) -> int:
    """Area-weighted mean tier from ``(label, area)`` pairs; unscored cells are
    excluded from the mean (but callers still count them)."""
    weight = 0.0
    weighted = 0.0
    for label, area in members:
        potential = label_potential(label)
        if potential >= 1:
            weight += area
            weighted += area * potential
    return round(weighted / weight) if weight > 0 else 0


def minmax_normalize(value: float, vmin: float, vmax: float) -> float:
    """The Excel model's ``1 + ((X-MIN)/(MAX-MIN))*99`` scale (1..100).

    A degenerate hour (every observed hex has the same volume) has no spread to
    normalize against; the observed value is the maximum, so it maps to 100.
    """
    if vmax <= vmin:
        return 100.0
    return 1.0 + ((value - vmin) / (vmax - vmin)) * 99.0


def recompute_hour_scores(hexes, hex_volumes: dict[int, float]) -> dict[int, dict]:
    """Per-hex live properties for one hour bucket.

    ``hexes`` are ``ActivityGridHex``-shaped rows; ``hex_volumes`` holds only
    hexes with a real mapped volume this hour. Hexes absent from
    ``hex_volumes`` are returned as ``no_data`` with null scores.
    """
    result = {hex_cell.hex_id: dict(NO_DATA) for hex_cell in hexes}
    observed = [hex_cell for hex_cell in hexes if hex_cell.hex_id in hex_volumes]
    if not observed:
        return result

    values = [hex_volumes[hex_cell.hex_id] for hex_cell in observed]
    vmin, vmax = min(values), max(values)
    scored = []
    for hex_cell in observed:
        norm_volume = minmax_normalize(hex_volumes[hex_cell.hex_id], vmin, vmax)
        score = (HEX_AHP_WEIGHTS["volume"] * norm_volume
                 + HEX_AHP_WEIGHTS["poi"] * hex_cell.norm_poi
                 + HEX_AHP_WEIGHTS["penduduk"] * hex_cell.norm_penduduk)
        scored.append((hex_cell.hex_id, norm_volume, score))

    scored.sort(key=lambda item: (-item[2], item[0]))
    total = len(scored)
    for rank, (hex_id, norm_volume, score) in enumerate(scored, 1):
        _, label = quintile_classify(rank, total)
        result[hex_id] = {"norm_volume": norm_volume, "skor_total_ahp": score,
                          "ranking": rank, "ranking_total": total,
                          "klasifikasi_potensi": label, "data_status": "live"}
    return result


async def _primary_hex_by_segment(db, segment_ids: list[str]) -> dict[str, int]:
    """Longest-intersection hex per segment, in one query (``resolve_primary_hex`` bulk form)."""
    if not segment_ids:
        return {}
    overlap = func.ST_Length(func.ST_Intersection(ActivityGridHex.geometry, RoadSegment.geometry))
    stmt = (
        select(RoadSegment.road_segment_id, ActivityGridHex.hex_id)
        .join(ActivityGridHex, func.ST_Intersects(ActivityGridHex.geometry, RoadSegment.geometry))
        .where(RoadSegment.road_segment_id.in_(segment_ids))
        .distinct(RoadSegment.road_segment_id)
        .order_by(RoadSegment.road_segment_id, overlap.desc())
    )
    return {segment_id: hex_id for segment_id, hex_id in (await db.execute(stmt)).all()}


async def hourly_hex_volumes(db, hour_start: datetime) -> dict[int, float]:
    """Sum live vehicle volume per primary hex for the hour starting at ``hour_start``.

    Segments without a usable volume sample are skipped, so their hex simply
    never enters the result and later renders as ``no_data``.
    """
    filters = AnalyticsFilter(hour_start, hour_start + timedelta(hours=1))
    means = vehicle_segment_means(filters, BUCKETS["1h"])
    stmt = select(means.c.segment_id, *[means.c[f"{key}_veh_h"] for key in VEHICLE_KEYS])
    rows = (await db.execute(stmt)).mappings().all()

    per_segment: dict[str, float] = {}
    for row in rows:
        values = [row[f"{key}_veh_h"] for key in VEHICLE_KEYS]
        if all(value is None for value in values):
            continue
        per_segment[row["segment_id"]] = sum(value for value in values if value is not None)

    hex_by_segment = await _primary_hex_by_segment(db, list(per_segment))
    volumes: dict[int, float] = {}
    for segment_id, volume in per_segment.items():
        hex_id = hex_by_segment.get(segment_id)
        if hex_id is not None:
            volumes[hex_id] = volumes.get(hex_id, 0.0) + volume
    return volumes
