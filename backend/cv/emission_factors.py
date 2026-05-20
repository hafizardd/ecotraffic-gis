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

# PM Emission Factors g/kg
PM_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 2.2,
    "car":        0.03,
    "bus":        0.94,
    "truck":      0.94,
}

# NMVOC Emission Factors g/kg
NMVOC_EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 131.4,
    "car":        10.05,
    "bus":        1.92,
    "truck":      1.92,
}

DISTANCE = 1.0  # Assume each detected vehicle travels 1 km during the minute of observation

# Calculate fuel consumption per vehicle type in Kg
FUEL_CONSUMPTION_PER_VEHICLE = {
    vehicle: FUEL_CONSUMPTION[vehicle] * DISTANCE / 1000
    for vehicle in FUEL_CONSUMPTION
}

def calculate_emission(counts: dict[str, int]) -> dict:
    """
    Calculate CO₂ emission estimate from vehicle counts.

    Args:
        counts: {"car": int, "motorcycle": int, "bus": int, "truck": int}
                Any extra keys are ignored; missing keys are treated as 0.

    Returns:
        {
            "total_g_per_min":  float,   # grams CO₂ per minute
            "total_kg_per_hr":  float,   # kilograms CO₂ per hour
            "breakdown": {
                "car":        float,     # g CO₂/min contribution
                "motorcycle": float,
                "bus":        float,
                "truck":      float,
            }
        }

    Example:
        >>> calculate_emission({"car": 10, "motorcycle": 20, "bus": 2, "truck": 1})
        {
            "total_g_per_min": 2250.0,
            "total_kg_per_hr": 135.0,
            "breakdown": {"car": 1200.0, "motorcycle": 800.0, "bus": 700.0, "truck": 350.0}
        }
    """
    breakdown = {}
    total_co_g_per_min = 0.0
    total_nox_g_per_min = 0.0
    total_pm_g_per_min = 0.0
    total_nmvoc_g_per_min = 0.0

    for vehicle, factor in FUEL_CONSUMPTION_PER_VEHICLE.items():
        count = counts.get(vehicle, 0)
        co_contribution = count * factor * CO_EMISSION_FACTORS[vehicle]
        nox_contribution = count * factor * NOX_EMISSION_FACTORS[vehicle]
        pm_contribution = count * factor * PM_EMISSION_FACTORS[vehicle]
        nmvoc_contribution = count * factor * NMVOC_EMISSION_FACTORS[vehicle]
        breakdown[vehicle] = {
            "co_g_per_min": round(co_contribution, 2),
            "nox_g_per_min": round(nox_contribution, 2),
            "pm_g_per_min": round(pm_contribution, 2),
            "nmvoc_g_per_min": round(nmvoc_contribution, 2),
        }

        # breakdown[vehicle] = contribution
        total_co_g_per_min += co_contribution
        total_nox_g_per_min += nox_contribution
        total_pm_g_per_min += pm_contribution
        total_nmvoc_g_per_min += nmvoc_contribution

    return {
        "total_co_g_per_min": round(total_co_g_per_min, 2),
        "total_co_kg_per_hr": round(total_co_g_per_min * 60 / 1000, 4),
        "total_nox_g_per_min": round(total_nox_g_per_min, 2),
        "total_nox_kg_per_hr": round(total_nox_g_per_min * 60 / 1000, 4),
        "total_pm_g_per_min": round(total_pm_g_per_min, 2),
        "total_pm_kg_per_hr": round(total_pm_g_per_min * 60 / 1000, 4),
        "total_nmvoc_g_per_min": round(total_nmvoc_g_per_min, 2),
        "total_nmvoc_kg_per_hr": round(total_nmvoc_g_per_min * 60 / 1000, 4),
        "breakdown": breakdown,
    }