"""Proposal Tier-2 emission factors for segment-level calculations.

Factors are grams per vehicle-kilometre and are kept separate from the
legacy camera snapshot calculator until the segment pipeline is complete.
"""

from collections.abc import Mapping
import math


VEHICLE_CATEGORIES = (
    "motorcycle",
    "gasoline_car",
    "diesel_car",
    "bus",
    "truck",
)

POLLUTANTS = (
    "TSP",
    "NOx",
    "SO2",
    "HC",
    "CO",
    "CO2",
    "CH4",
    "N2O",
)

EMISSION_FACTORS: dict[str, dict[str, float]] = {
    "motorcycle": {
        "TSP": 0.24, "NOx": 0.29, "SO2": 0.008, "HC": 5.9,
        "CO": 14.0, "CO2": 3180.0, "CH4": 0.26, "N2O": 0.002,
    },
    "gasoline_car": {
        "TSP": 0.01, "NOx": 2.0, "SO2": 0.026, "HC": 4.0,
        "CO": 40.0, "CO2": 3180.0, "CH4": 0.07, "N2O": 0.005,
    },
    "diesel_car": {
        "TSP": 0.53, "NOx": 3.5, "SO2": 0.44, "HC": 0.2,
        "CO": 2.8, "CO2": 3172.0, "CH4": 0.01, "N2O": 0.014,
    },
    "bus": {
        "TSP": 1.4, "NOx": 11.9, "SO2": 0.93, "HC": 1.3,
        "CO": 11.0, "CO2": 3172.0, "CH4": 0.06, "N2O": 0.031,
    },
    "truck": {
        "TSP": 1.4, "NOx": 17.7, "SO2": 0.82, "HC": 1.8,
        "CO": 9.4, "CO2": 3172.0, "CH4": 0.01, "N2O": 0.031,
    },
}


def validate_emission_factors(
    factors: Mapping[str, Mapping[str, float]] = EMISSION_FACTORS,
) -> None:
    """Reject missing, non-numeric, or non-finite proposal factors."""
    missing_categories = set(VEHICLE_CATEGORIES) - set(factors)
    if missing_categories:
        raise ValueError(f"missing vehicle categories: {sorted(missing_categories)}")

    for category in VEHICLE_CATEGORIES:
        missing_pollutants = set(POLLUTANTS) - set(factors[category])
        if missing_pollutants:
            raise ValueError(
                f"missing factors for {category}: {sorted(missing_pollutants)}"
            )
        for pollutant in POLLUTANTS:
            value = factors[category][pollutant]
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"factor for {category}/{pollutant} must be finite and non-negative"
                )


validate_emission_factors()
