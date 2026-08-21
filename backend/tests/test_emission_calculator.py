import pytest

from cv.emission_factors import (
    CO_EMISSION_FACTORS,
    FUEL_CONSUMPTION_PER_VEHICLE,
    NMVOC_EMISSION_FACTORS,
    NOX_EMISSION_FACTORS,
    PM_EMISSION_FACTORS,
    calculate_emission,
)


VEHICLE_TYPES = {"car", "motorcycle", "bus", "truck"}


def test_current_multi_pollutant_calculation_contract():
    result = calculate_emission(
        {"car": 10, "motorcycle": 20, "bus": 2, "truck": 1}
    )

    assert result == {
        "total_co_g_per_min": 413.35,
        "total_co_kg_per_hr": 24.8009,
        "total_nox_g_per_min": 34.79,
        "total_nox_kg_per_hr": 2.0871,
        "total_pm_g_per_min": 2.24,
        "total_pm_kg_per_hr": 0.1343,
        "total_nmvoc_g_per_min": 100.4,
        "total_nmvoc_kg_per_hr": 6.0238,
        "breakdown": {
            "motorcycle": {
                "co_g_per_min": 348.39,
                "nox_g_per_min": 4.65,
                "pm_g_per_min": 1.54,
                "nmvoc_g_per_min": 91.98,
            },
            "car": {
                "co_g_per_min": 59.5,
                "nox_g_per_min": 6.11,
                "pm_g_per_min": 0.02,
                "nmvoc_g_per_min": 7.04,
            },
            "bus": {
                "co_g_per_min": 3.64,
                "nox_g_per_min": 16.02,
                "pm_g_per_min": 0.45,
                "nmvoc_g_per_min": 0.92,
            },
            "truck": {
                "co_g_per_min": 1.82,
                "nox_g_per_min": 8.01,
                "pm_g_per_min": 0.23,
                "nmvoc_g_per_min": 0.46,
            },
        },
    }


def test_zero_and_missing_vehicle_counts_are_zero():
    result = calculate_emission({})

    assert result["total_co_g_per_min"] == 0.0
    assert result["total_nox_g_per_min"] == 0.0
    assert result["total_pm_g_per_min"] == 0.0
    assert result["total_nmvoc_g_per_min"] == 0.0
    assert set(result["breakdown"]) == VEHICLE_TYPES
    assert all(
        value == 0.0
        for pollutant_values in result["breakdown"].values()
        for value in pollutant_values.values()
    )


def test_extra_vehicle_classes_are_ignored():
    assert calculate_emission({"bicycle": 100}) == calculate_emission({})


@pytest.mark.parametrize(
    ("pollutant", "factors"),
    [
        ("co", CO_EMISSION_FACTORS),
        ("nox", NOX_EMISSION_FACTORS),
        ("pm", PM_EMISSION_FACTORS),
        ("nmvoc", NMVOC_EMISSION_FACTORS),
    ],
)
def test_single_vehicle_breakdown_uses_existing_factors(pollutant, factors):
    for vehicle in VEHICLE_TYPES:
        result = calculate_emission({vehicle: 1})
        expected = round(
            FUEL_CONSUMPTION_PER_VEHICLE[vehicle] * factors[vehicle],
            2,
        )

        assert result["breakdown"][vehicle][f"{pollutant}_g_per_min"] == expected
