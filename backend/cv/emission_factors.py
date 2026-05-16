# Grams of CO₂ emitted per vehicle per minute (idling / slow urban traffic)
EMISSION_FACTORS: dict[str, float] = {
    "motorcycle": 40.0,
    "car":        120.0,
    "bus":        350.0,
    "truck":      350.0,
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
    total_g_per_min = 0.0

    for vehicle, factor in EMISSION_FACTORS.items():
        count = counts.get(vehicle, 0)
        contribution = count * factor
        breakdown[vehicle] = contribution
        total_g_per_min += contribution

    return {
        "total_g_per_min": round(total_g_per_min, 2),
        "total_kg_per_hr": round(total_g_per_min * 60 / 1000, 4),
        "breakdown": breakdown,
    }