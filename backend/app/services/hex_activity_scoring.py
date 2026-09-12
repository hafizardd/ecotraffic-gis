"""Live hourly re-scoring of the activity-potential hex grid.

Only the volume input is recomputed from live ``segment_emissions`` rows; the
offline ``norm_poi``/``norm_penduduk`` and the fixed AHP weights are reused
as-is. A hex with no mapped segment (or no volume sample) in the hour keeps a
``None`` score rather than a fabricated zero, mirroring the pipeline norm that
missing spatial data is omitted, never invented.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
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

    A degenerate hour (every observed hex has the same volume) has no spread to
    normalize against; the observed value is the maximum, so it maps to 100.
    """
    if vmax <= vmin:
        return 100.0
    return 1.0 + ((value - vmin) / (vmax - vmin)) * 99.0


# Fixed score -> tier bands, mirroring the frontend ACTIVITY_SCORE_RAMP stops
# (1/25/50/75/100). Used only for cells without a live rank (fallback), so a
# borrowed cell can still read Rendah/Tinggi/Sangat Tinggi without claiming a
# position in the observed ranking.
_SCORE_BANDS = ((25.0, "Sangat Rendah"), (50.0, "Rendah"), (75.0, "Sedang"), (100.0, "Tinggi"))


def score_band_label(score: float | None) -> str | None:
    if score is None:
        return None
    for upper, label in _SCORE_BANDS:
        if score < upper:
            return label
    return "Sangat Tinggi"


def _ahp_score(cell, norm_volume: float) -> float:
    return (HEX_AHP_WEIGHTS["volume"] * norm_volume
            + HEX_AHP_WEIGHTS["poi"] * cell.norm_poi
            + HEX_AHP_WEIGHTS["penduduk"] * cell.norm_penduduk)


def _nearest_scored_hex(centroid: tuple[float, float], centroids: dict[int, tuple[float, float]],
                        scored_ids: set[int]) -> int | None:
    """Nearest hex that has a real volume this hour (squared lon/lat distance)."""
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
    """Per-hex live properties for one hour bucket.

    ``hexes`` are ``ActivityGridHex``-shaped rows; ``hex_volumes`` holds only
    hexes with a real mapped volume this hour (as ``HexHourData`` or a plain
    ``{hex_id: float}``). Without ``centroids``, hexes absent from the volumes
    stay ``no_data`` with null scores and a ``no_data_reason``. With
    ``centroids``, they inherit the nearest scored hex's volume behind a
    ``data_status="fallback"`` flag, so the map has no unexplained grey cells
    while still distinguishing borrowed values from observed ones.
    """
    volumes, mapped = _normalize_hour_data(hex_volumes)
    result = {hex_cell.hex_id: dict(NO_DATA) for hex_cell in hexes}
    observed = [hex_cell for hex_cell in hexes if hex_cell.hex_id in volumes]
    if not observed:
        for hex_cell in hexes:
            result[hex_cell.hex_id]["no_data_reason"] = _no_data_reason(hex_cell.hex_id, mapped)
        return result

    values = [volumes[hex_cell.hex_id].volume for hex_cell in observed]
    vmin, vmax = min(values), max(values)
    scored = []
    for hex_cell in observed:
        norm_volume = minmax_normalize(volumes[hex_cell.hex_id].volume, vmin, vmax)
        scored.append((hex_cell.hex_id, norm_volume, _ahp_score(hex_cell, norm_volume)))

    scored.sort(key=lambda item: (-item[2], item[0]))
    total = len(scored)
    for rank, (hex_id, norm_volume, score) in enumerate(scored, 1):
        _, label = quintile_classify(rank, total)
        data = volumes[hex_id]
        result[hex_id] = {"norm_volume": norm_volume, "skor_total_ahp": score,
                          "ranking": rank, "ranking_total": total,
                          "klasifikasi_potensi": label, "data_status": "live",
                          "source_segments": list(data.segment_ids),
                          "is_interpolated": data.interpolated, "no_data_reason": None}

    if centroids:
        scored_ids = {hex_cell.hex_id for hex_cell in observed}
        for hex_cell in hexes:
            if hex_cell.hex_id in scored_ids or hex_cell.hex_id not in centroids:
                continue
            source_id = _nearest_scored_hex(centroids[hex_cell.hex_id], centroids, scored_ids)
            if source_id is None:
                continue
            source = volumes[source_id]
            norm_volume = minmax_normalize(source.volume, vmin, vmax)
            score = _ahp_score(hex_cell, norm_volume)
            result[hex_cell.hex_id] = {
                "norm_volume": norm_volume, "skor_total_ahp": score,
                "ranking": None, "ranking_total": total,
                "klasifikasi_potensi": score_band_label(score), "data_status": FALLBACK_STATUS,
                "fallback_from": source_id, "source_segments": [],
                "is_interpolated": source.interpolated,
                "no_data_reason": _no_data_reason(hex_cell.hex_id, mapped),
            }

    # Anything still unscored (centroids absent or no scored neighbour) explains itself.
    for hex_cell in hexes:
        entry = result[hex_cell.hex_id]
        if entry["data_status"] == "no_data" and entry.get("no_data_reason") is None:
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
