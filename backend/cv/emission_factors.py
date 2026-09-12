from collections.abc import Mapping


# Fuel consumption g/km
FUEL_CONSUMPTION: dict[str, float] = {
    "motorcycle": 35.0,
    "car":        70.0,
    "bus":        240.0,
    "truck":      240.0,
}

# CO Emission Factors g/kg
CO_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 497.7,
    "car":        85.0,
    "bus":        7.58,
    "truck":      7.58,
}

# NOx Emission Factors g/kg
NOX_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 6.64,
    "car":        8.73,
    "bus":        33.37,
    "truck":      33.37,
}

# TSP Emission Factors g/kg
TSP_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 2.2,
    "car":        0.03,
    "bus":        0.94,
    "truck":      0.94,
}

# HC Emission Factors g/kg
HC_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 131.4,
    "car":        10.05,
    "bus":        1.92,
    "truck":      1.92,
}

# SO₂, CO₂, CH₄, and N₂O emission factors g/kg fuel.
SO2_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 0.04,
    "car": 0.05,
    "bus": 0.12,
    "truck": 0.12,
}
CO2_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 3180.0,
    "car": 3180.0,
    "bus": 3200.0,
    "truck": 3200.0,
}
CH4_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 2.0,
    "car": 0.8,
    "bus": 0.3,
    "truck": 0.3,
}
N2O_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 0.02,
    "car": 0.02,
    "bus": 0.04,
    "truck": 0.04,
}

DISTANCE = 1.0  # Assume each detected vehicle travels 1 km during the minute of observation

# Calculate fuel consumption per vehicle type in Kg
FUEL_CONSUMPTION_PER_VEHICLE = {
    vehicle: FUEL_CONSUMPTION[vehicle] * DISTANCE / 1000
    for vehicle in FUEL_CONSUMPTION
}

def calculate_emission(counts: Mapping[str, int | float]) -> dict:
    """
    Calculate multi-pollutant emission-rate estimates from snapshot counts.

    Args:
        counts: Numeric observed counts for car, motorcycle, bus, and truck.
                Fractional values are supported for temporal snapshot means.
                Extra keys are ignored; missing keys are treated as zero.

    Returns:
        {
        Total TSP, NOx, SO₂, HC, CO, CO₂, CH₄, and N₂O rate fields plus
            the per-vehicle breakdown.
        }

    Example:
        >>> calculate_emission({"car": 10, "motorcycle": 20, "bus": 2, "truck": 1})
        A mapping containing the eight ``total_<pollutant>`` rate pairs and
        a per-vehicle breakdown.
    """
    breakdown = {}
    totals = {pollutant: 0.0 for pollutant in (
        "tsp", "nox", "so2", "hc", "co", "co2", "ch4", "n2o"
    )}
    factors = {
        "tsp": TSP_EMISSION_FACTORS,
        "nox": NOX_EMISSION_FACTORS,
        "so2": SO2_EMISSION_FACTORS,
        "hc": HC_EMISSION_FACTORS,
        "co": CO_EMISSION_FACTORS,
        "co2": CO2_EMISSION_FACTORS,
        "ch4": CH4_EMISSION_FACTORS,
        "n2o": N2O_EMISSION_FACTORS,
    }

    for vehicle, factor in FUEL_CONSUMPTION_PER_VEHICLE.items():
        count = counts.get(vehicle, 0)
        contributions = {
            pollutant: count * factor * pollutant_factors[vehicle]
            for pollutant, pollutant_factors in factors.items()
        }
        breakdown[vehicle] = {
            f"{pollutant}_g_per_min": round(value, 2)
            for pollutant, value in contributions.items()
        }
        for pollutant, value in contributions.items():
            totals[pollutant] += value

    return {
        **{
            f"total_{pollutant}_g_per_min": round(value, 2)
            for pollutant, value in totals.items()
        },
        **{
            f"total_{pollutant}_kg_per_hr": round(value * 60 / 1000, 4)
            for pollutant, value in totals.items()
        },
        "breakdown": breakdown,
    }
