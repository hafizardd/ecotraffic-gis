"""H3 re-bucketing of the activity-potential hex grid.

The native grid is a fixed offline AHP snapshot (~±100 m cells). Zoomed-out
views are too dense to render, so native cells are rolled up into H3 cells at a
coarser resolution. Only geometry and the numeric aggregate change; the
per-hour scoring still happens on the native cells, so the map and the detail
panel keep agreeing.

`fine` (zoom >= 14) is the native grid and never passes through H3.
"""

import math

import h3

from app.services.hex_activity_scoring import POTENTIAL_LABELS, aggregate_potential

# Zoomed-out LOD -> H3 resolution.
LOD_RESOLUTIONS = {"coarse": 6, "medium": 7, "sub": 8}


def h3_cell(lon: float, lat: float, resolution: int) -> str:
    """H3 cell containing ``(lon, lat)`` (h3-py takes lat/lng)."""
    return h3.latlng_to_cell(float(lat), float(lon), resolution)


def h3_boundary_geojson(cell: str) -> list[list[float]]:
    """Closed ``[lon, lat]`` ring for an H3 cell (GeoJSON axis order)."""
    ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(cell)]
    ring.append(ring[0])
    return ring


def in_bbox(lon: float, lat: float, bounds) -> bool:
    if not bounds:
        return True
    min_lon, min_lat, max_lon, max_lat = bounds
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def _percentile(ordered: list[float], q: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def quantile_breaks(values, classes: int = 5) -> list[float] | None:
    """``classes`` quantile cut points (min..max) for a choropleth ramp.

    Returns None for a degenerate distribution (no spread / too few values) so
    the caller falls back to discrete classification tiers instead of emitting
    an invalid MapLibre interpolate with equal stops.
    """
    ordered = sorted(float(v) for v in values if v is not None)
    if len(ordered) < 2:
        return None
    vmin, vmax = ordered[0], ordered[-1]
    if vmax <= vmin:
        return None
    breaks = [_percentile(ordered, index / (classes - 1)) for index in range(classes)]
    for index in range(1, classes):
        if breaks[index] <= breaks[index - 1]:
            breaks[index] = breaks[index - 1] + (vmax - vmin) * 1e-6
    return breaks


def _score_of(cell, scores):
    if scores is not None:
        return scores.get(cell.hex_id, {}).get("skor_total_ahp")
    return cell.skor_total_ahp


def _label_of(cell, scores):
    if scores is not None:
        return scores.get(cell.hex_id, {}).get("klasifikasi_potensi")
    return cell.klasifikasi_potensi


def aggregate_cells(members, scores) -> dict:
    """Roll native ``(cell, lon, lat)`` members into one H3 bucket's metrics.

    Raw counts sum; the AHP score is the area-weighted mean of scored members
    (None when none are scored); the class label is the area-weighted tier,
    matching the offline model's rule.
    """
    total_area = sum(float(cell.luas_km2) for cell, _, _ in members)
    score_weight = 0.0
    weighted_score = 0.0
    for cell, _, _ in members:
        score = _score_of(cell, scores)
        if score is not None:
            score_weight += float(cell.luas_km2)
            weighted_score += float(cell.luas_km2) * float(score)
    potential = aggregate_potential(
        [(_label_of(cell, scores), float(cell.luas_km2)) for cell, _, _ in members]
    )
    return {
        "luas_km2": total_area,
        "poi_total": sum(int(cell.poi_total) for cell, _, _ in members),
        "penduduk": sum(int(cell.penduduk) for cell, _, _ in members),
        "skor_total_ahp": (weighted_score / score_weight) if score_weight > 0 else None,
        "klasifikasi_potensi": POTENTIAL_LABELS.get(potential),
    }
