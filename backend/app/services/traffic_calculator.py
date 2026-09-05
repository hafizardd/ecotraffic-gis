"""Segment traffic volume and vehicle-kilometre calculations."""

from collections.abc import Mapping
import math

from cv.proposal_emission_factors import VEHICLE_CATEGORIES


def _validate_non_negative(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return value


def volume_per_hour(
    raw_counts: Mapping[str, int | float],
    observation_duration_seconds: float,
    *,
    already_hourly: bool = False,
) -> dict[str, float]:
    duration = float(observation_duration_seconds)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("observation duration must be finite and greater than zero")
    multiplier = 1.0 if already_hourly else 3600.0 / duration
    return {
        category: _validate_non_negative(raw_counts.get(category, 0), f"count for {category}") * multiplier
        for category in VEHICLE_CATEGORIES
    }


def vkt_by_category(volume: Mapping[str, int | float], road_length_km: float) -> dict[str, float]:
    length = float(road_length_km)
    if not math.isfinite(length) or length <= 0:
        raise ValueError("road_length_km must be finite and greater than zero")
    return {
        category: _validate_non_negative(volume.get(category, 0), f"volume for {category}") * length
        for category in VEHICLE_CATEGORIES
    }
