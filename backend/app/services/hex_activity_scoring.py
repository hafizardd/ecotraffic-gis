"""Live hourly re-scoring of the activity-potential hex grid.

Reproduces the offline Excel model (``Skoring Grid Potensi Timbulan
Kemacetan.xlsx``) at request time: each grid is scored from its three
normalized AHP inputs, ranked across the whole grid, then split evenly into
five classes by rank (``CHOOSE(ROUNDUP(rank*5/total))``).

Volume adapts to the data source: a grid with a real hourly volume (live,
historical, or gap-filled/interpolated) uses it; a grid without one uses its
own stored historical ``volume_mean``. POI and population are static offline
inputs. Grids with neither an hourly volume nor a ``volume_mean`` stay
``no_data`` - missing spatial data is omitted, never invented.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.services.classification import quintile_classify
from app.services.emission_analytics import (
    BUCKETS,
    VEHICLE_KEYS,
    AnalyticsFilter,
    source_mode_expression,
    vehicle_segment_means,
)
from app.services.segment_estimate import is_interpolated_of, latest_observed_facts

# 'AHP Bobot' B29-B31 from the Excel model (CR = 0.0096). Same values the
# offline importer verifies against; full precision so the live recomputation
# never drifts from the stored snapshot.
HEX_AHP_WEIGHTS = {
    "volume": 0.538961038961039,
    "poi": 0.2972582972582973,
    "penduduk": 0.16378066378066378,
}

NO_DATA = {"norm_volume": None, "skor_total_ahp": None, "ranking": None,
           "klasifikasi_potensi": None, "data_status": "no_data", "no_data_reason": None}

# Presentation fallback: a hex with no mapped segment keeps a score borrowed
# from the nearest scored hex, flagged so the UI never presents it as observed.
FALLBACK_STATUS = "fallback"

# Why a hex had no live volume; surfaced so the UI can explain grey/borrowed cells.
NO_MAPPED_SEGMENT = "no_mapped_segment"
MAPPED_BUT_NO_VOLUME = "mapped_but_no_volume"

# Coarse LOD is a presentation approximation: fixed cells are unioned into
# larger super-cells and colored by the area-weighted mean of their member
# tiers. It is not an independently scored cell, so hex_id stays null.
POTENTIAL_LABELS = {1: "Sangat Rendah", 2: "Rendah", 3: "Sedang", 4: "Tinggi", 5: "Sangat Tinggi"}


@dataclass(frozen=True, slots=True)
class HexHourVolume:
    """One hex's hourly volume plus the provenance behind it."""
    volume: float
    segment_ids: tuple[str, ...] = ()
    interpolated: bool = False


@dataclass(frozen=True, slots=True)
class HexHourData:
    """One hour's per-hex volumes and the set of hexes any mapped segment reaches."""
    volumes: dict[int, HexHourVolume] = field(default_factory=dict)
    mapped_hex_ids: frozenset[int] = frozenset()



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

    A degenerate grid (every reference value equal, e.g. a single cell) has no
    spread to normalize against; the value is the maximum, so it maps to 100.
    """
    if vmax <= vmin:
        return 100.0
    return 1.0 + ((value - vmin) / (vmax - vmin)) * 99.0


def _ahp_score(cell, norm_volume: float) -> float:
    return (HEX_AHP_WEIGHTS["volume"] * norm_volume
            + HEX_AHP_WEIGHTS["poi"] * cell.norm_poi
            + HEX_AHP_WEIGHTS["penduduk"] * cell.norm_penduduk)


def _reference_volume_range(hexes) -> tuple[float, float] | None:
    """Grid-wide ``volume_mean`` range: the Excel Min-Max normalization basis.

    Used only when an hour has no observed volume at all, so the fallback grid
    still normalizes against the model's own ``MIN``/``MAX`` scale.
    """
    values = [float(cell.volume_mean) for cell in hexes if getattr(cell, "volume_mean", None) is not None]
    return (min(values), max(values)) if values else None


def _nearest_scored_hex(centroid: tuple[float, float], centroids: dict[int, tuple[float, float]],
                        scored_ids: set[int]) -> int | None:
    """Nearest hex with a real volume this hour (squared lon/lat distance)."""
    lon, lat = centroid
    best_id: int | None = None
    best_distance = float("inf")
    for hex_id in scored_ids:
        other = centroids.get(hex_id)
        if other is None:
            continue
        distance = (lon - other[0]) ** 2 + (lat - other[1]) ** 2
        if distance < best_distance:
            best_id, best_distance = hex_id, distance
    return best_id


def _normalize_hour_data(hex_volumes) -> tuple[dict[int, HexHourVolume], frozenset[int]]:
    """Accept ``HexHourData`` or a bare ``{hex_id: float}`` mapping (unit tests)."""
    if isinstance(hex_volumes, HexHourData):
        return hex_volumes.volumes, hex_volumes.mapped_hex_ids
    volumes = {
        hex_id: value if isinstance(value, HexHourVolume) else HexHourVolume(float(value))
        for hex_id, value in hex_volumes.items()
    }
    return volumes, frozenset(volumes)


def _no_data_reason(hex_id: int, mapped: frozenset[int]) -> str:
    return MAPPED_BUT_NO_VOLUME if hex_id in mapped else NO_MAPPED_SEGMENT


def recompute_hour_scores(hexes, hex_volumes, centroids: dict[int, tuple[float, float]] | None = None) -> dict[int, dict]:
    """Per-hex live properties for one hour, mirroring the Excel rank model.

    ``hexes`` are ``ActivityGridHex``-shaped rows; ``hex_volumes`` holds only
    hexes with a real volume this hour (as ``HexHourData`` or a plain
    ``{hex_id: float}``). Volume adapts to the data source:

    * observed grids use their hourly volume (live, historical, interpolated);
    * a grid without one borrows the nearest observed grid's volume and is
      flagged ``data_status="fallback"`` with ``fallback_from``;
    * if no observed volume exists in the hour (or no centroid is available to
      borrow), the grid falls back to its own stored ``volume_mean``.

    Scores are normalized against the observed-hour range (the grid-wide
    ``volume_mean`` range when nothing is observed), all scored grids are ranked
    together, and the five Excel classes are assigned by rank.
    """
    volumes, mapped = _normalize_hour_data(hex_volumes)
    observed_ids = set(volumes)
    candidates: list[tuple] = []

    if observed_ids:
        values = [entry.volume for entry in volumes.values()]
        vmin, vmax = min(values), max(values)
        for hex_cell in hexes:
            hourly = volumes.get(hex_cell.hex_id)
            if hourly is not None:
                norm_volume = minmax_normalize(hourly.volume, vmin, vmax)
                score = _ahp_score(hex_cell, norm_volume)
                candidates.append((hex_cell, norm_volume, score, "live", hourly, None, hourly.interpolated))
                continue
            source_id = None
            centroid = centroids.get(hex_cell.hex_id) if centroids else None
            if centroid is not None:
                source_id = _nearest_scored_hex(centroid, centroids, observed_ids)
            if source_id is not None:
                source = volumes[source_id]
                volume, interpolated = source.volume, source.interpolated
            else:
                baseline = getattr(hex_cell, "volume_mean", None)
                if baseline is None:
                    continue
                volume, interpolated = float(baseline), False
            norm_volume = minmax_normalize(volume, vmin, vmax)
            candidates.append((hex_cell, norm_volume, _ahp_score(hex_cell, norm_volume),
                               FALLBACK_STATUS, None, source_id, interpolated))
    else:
        reference = _reference_volume_range(hexes)
        if reference is not None:
            vmin, vmax = reference
            for hex_cell in hexes:
                baseline = getattr(hex_cell, "volume_mean", None)
                if baseline is None:
                    continue
                norm_volume = minmax_normalize(float(baseline), vmin, vmax)
                candidates.append((hex_cell, norm_volume, _ahp_score(hex_cell, norm_volume),
                                   FALLBACK_STATUS, None, None, False))

    result = {hex_cell.hex_id: dict(NO_DATA) for hex_cell in hexes}

    # One global ranking and one quintile split for observed and estimated grids
    # alike, so class never contradicts score (Excel: RANK over the whole grid).
    candidates.sort(key=lambda item: (-item[2], item[0].hex_id))
    total = len(candidates)
    for rank, (hex_cell, norm_volume, score, status, data, source_id, interpolated) in enumerate(candidates, 1):
        _, label = quintile_classify(rank, total)
        entry = {
            "norm_volume": norm_volume, "skor_total_ahp": score,
            "ranking": rank, "ranking_total": total,
            "klasifikasi_potensi": label, "data_status": status,
            "source_segments": list(data.segment_ids) if data else [],
            "is_interpolated": interpolated,
            "no_data_reason": None if status == "live" else _no_data_reason(hex_cell.hex_id, mapped),
        }
        if source_id is not None:
            entry["fallback_from"] = source_id
        result[hex_cell.hex_id] = entry

    for hex_cell in hexes:
        entry = result[hex_cell.hex_id]
        if entry["data_status"] == "no_data":
            entry["no_data_reason"] = _no_data_reason(hex_cell.hex_id, mapped)
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


async def _interpolated_segments(db, hour_start: datetime) -> set[str]:
    """Segments whose REPLAY fact for this hour is a gap-filled (interpolated) hour."""
    stmt = (
        select(RoadSegment.road_segment_id)
        .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
        .where(
            SegmentEmission.period_start >= hour_start,
            SegmentEmission.period_start < hour_start + timedelta(hours=1),
            SegmentEmission.ahp_metadata["calculation_metadata"]["is_interpolated"].astext == "true",
        )
        .distinct()
    )
    return set((await db.execute(stmt)).scalars().all())


async def hourly_hex_volumes(db, hour_start: datetime) -> HexHourData:
    """Sum live vehicle volume per primary hex for the hour starting at ``hour_start``.

    Segments without a usable volume sample are skipped (their hex never enters
    the volume map), but every hex any mapped segment reaches is reported in
    ``mapped_hex_ids`` so a missing hex can explain *why* it has no volume.
    """
    filters = AnalyticsFilter(hour_start, hour_start + timedelta(hours=1))
    means = vehicle_segment_means(filters, BUCKETS["1h"])
    stmt = select(means.c.segment_id, *[means.c[f"{key}_veh_h"] for key in VEHICLE_KEYS])
    rows = (await db.execute(stmt)).mappings().all()

    per_segment: dict[str, float] = {}
    segment_ids: list[str] = []
    for row in rows:
        segment_ids.append(row["segment_id"])
        values = [row[f"{key}_veh_h"] for key in VEHICLE_KEYS]
        if all(value is None for value in values):
            continue
        per_segment[row["segment_id"]] = sum(value for value in values if value is not None)

    hex_by_segment = await _primary_hex_by_segment(db, segment_ids)
    mapped_hex_ids = frozenset(hex_id for hex_id in hex_by_segment.values() if hex_id is not None)
    interpolated = await _interpolated_segments(db, hour_start)

    grouped: dict[int, dict] = {}
    for segment_id, volume in per_segment.items():
        hex_id = hex_by_segment.get(segment_id)
        if hex_id is None:
            continue
        entry = grouped.setdefault(hex_id, {"volume": 0.0, "segment_ids": [], "interpolated": False})
        entry["volume"] += volume
        entry["segment_ids"].append(segment_id)
        entry["interpolated"] = entry["interpolated"] or segment_id in interpolated

    volumes = {
        hex_id: HexHourVolume(entry["volume"], tuple(sorted(entry["segment_ids"])), entry["interpolated"])
        for hex_id, entry in grouped.items()
    }
    return HexHourData(volumes=volumes, mapped_hex_ids=mapped_hex_ids)


async def latest_hex_volumes(db) -> HexHourData:
    """Sum each segment's newest observed volume per primary hex (live lens).

    Unlike :func:`hourly_hex_volumes` (one fixed hour bucket), this reads the
    latest non-SYNTHETIC fact per segment: the two live tracking cameras'
    segments move as their ``SegmentEmission`` rows are reconciled, while every
    other hex holds its newest REPLAY/observed value.
    """
    facts = await latest_observed_facts(db)
    per_segment: dict[str, float] = {}
    interpolated: set[str] = set()
    for segment_id, emission in facts.items():
        volume = emission.volume_per_hour or {}
        values = [volume.get(key) for key in VEHICLE_KEYS]
        if all(value is None for value in values):
            continue
        per_segment[segment_id] = sum(float(value) for value in values if value is not None)
        if is_interpolated_of(emission):
            interpolated.add(segment_id)

    hex_by_segment = await _primary_hex_by_segment(db, list(facts))
    mapped_hex_ids = frozenset(hex_id for hex_id in hex_by_segment.values() if hex_id is not None)

    grouped: dict[int, dict] = {}
    for segment_id, volume in per_segment.items():
        hex_id = hex_by_segment.get(segment_id)
        if hex_id is None:
            continue
        entry = grouped.setdefault(hex_id, {"volume": 0.0, "segment_ids": [], "interpolated": False})
        entry["volume"] += volume
        entry["segment_ids"].append(segment_id)
        entry["interpolated"] = entry["interpolated"] or segment_id in interpolated

    volumes = {
        hex_id: HexHourVolume(entry["volume"], tuple(sorted(entry["segment_ids"])), entry["interpolated"])
        for hex_id, entry in grouped.items()
    }
    return HexHourData(volumes=volumes, mapped_hex_ids=mapped_hex_ids)


# --- static 24h profile addressing (shared by the map route and Bang Jo) -------


async def all_cells_with_centroids(db):
    """All native cells plus their centroid lon/lat, for the fallback distance test."""
    rows = (await db.execute(
        select(
            ActivityGridHex,
            text("ST_X(ST_Centroid(activity_grid_hexes.geometry))::float"),
            text("ST_Y(ST_Centroid(activity_grid_hexes.geometry))::float"),
        )
    )).all()
    cells = [row[0] for row in rows]
    centroids = {row[0].hex_id: (row[1], row[2]) for row in rows}
    return cells, centroids


async def hour_scores(db, hour: datetime) -> tuple[list, dict[int, dict]]:
    """Global (whole-grid) live scores for one hour, so map and panel agree."""
    cells, centroids = await all_cells_with_centroids(db)
    scores = recompute_hour_scores(cells, await hourly_hex_volumes(db, hour), centroids)
    return cells, scores


async def live_scores(db) -> tuple[list, dict[int, dict]]:
    """Global scores from each segment's newest observed fact (live lens)."""
    cells, centroids = await all_cells_with_centroids(db)
    scores = recompute_hour_scores(cells, await latest_hex_volumes(db), centroids)
    return cells, scores


async def _max_bucket(db, where) -> datetime | None:
    bucket = func.to_timestamp(func.floor(func.extract("epoch", SegmentEmission.period_start) / 3600) * 3600)
    value = (await db.execute(select(func.max(bucket)).where(where))).scalar_one_or_none()
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


async def profile_anchor(db) -> datetime | None:
    """Anchor of the static 24h profile.

    Prefers the precomputed REPLAY dataset so its buckets stay addressable on
    any requested day; falls back to the newest observed sample when no REPLAY
    rows exist yet (e.g. a live-only dev database).
    """
    replay = await _max_bucket(db, source_mode_expression() == "REPLAY")
    if replay is not None:
        return replay
    return await _max_bucket(db, source_mode_expression().notin_(["SYNTHETIC"]))


def canonical_hour(anchor: datetime, requested: datetime | None) -> datetime:
    """Map a requested instant onto the anchor day's bucket with the same UTC hour-of-day.

    The precomputed REPLAY facts are one static 24h profile, so any calendar day
    resolves to the same underlying buckets ("view lens") without duplicating rows.
    """
    hour_of_day = requested.hour if requested is not None else anchor.hour
    return anchor - timedelta(hours=(anchor.hour - hour_of_day) % 24)


async def profile_hour(db, requested: datetime | None) -> datetime | None:
    anchor = await profile_anchor(db)
    return canonical_hour(anchor, requested) if anchor is not None else None


async def available_hours(db) -> list[datetime]:
    """The static profile's 24 hourly buckets (oldest first)."""
    anchor = await profile_anchor(db)
    if anchor is None:
        return []
    return [anchor - timedelta(hours=23 - index) for index in range(24)]
