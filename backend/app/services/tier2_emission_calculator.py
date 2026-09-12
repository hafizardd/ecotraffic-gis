"""Proposal Tier-2 segment emission calculation in grams per hour."""

from collections.abc import Mapping
import math

from cv.proposal_emission_factors import EMISSION_FACTORS, POLLUTANTS, VEHICLE_CATEGORIES, validate_emission_factors


def calculate_tier2_emissions(
    vkt_km_h: Mapping[str, int | float],
    *,
    control_efficiency: float = 0.0,
    emission_factors: Mapping[str, Mapping[str, float]] = EMISSION_FACTORS,
) -> dict:
    validate_emission_factors(emission_factors)
    control_efficiency = float(control_efficiency)
    if not math.isfinite(control_efficiency) or not 0 <= control_efficiency <= 100:
        raise ValueError("control_efficiency must be between 0 and 100 percent")
    correction = (100.0 - control_efficiency) / 100.0
    by_category = {}
    totals = {pollutant: 0.0 for pollutant in POLLUTANTS}
    for category in VEHICLE_CATEGORIES:
        vkt = float(vkt_km_h.get(category, 0))
        if not math.isfinite(vkt) or vkt < 0:
            raise ValueError(f"VKT for {category} must be finite and non-negative")
        by_category[category] = {}
        for pollutant in POLLUTANTS:
            value = vkt * emission_factors[category][pollutant] * correction
            by_category[category][pollutant] = value
            totals[pollutant] += value
    return {
        "totals_g_h": totals,
        "by_category_g_h": by_category,
        "control_efficiency": control_efficiency,
        "correction": correction,
    }
