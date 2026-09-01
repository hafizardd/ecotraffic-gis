import pytest

from cv.emission_factors import (
    CO_EMISSION_FACTORS,
    FUEL_CONSUMPTION_PER_VEHICLE,
    HC_EMISSION_FACTORS,
    NOX_EMISSION_FACTORS,
    SO2_EMISSION_FACTORS,
    TSP_EMISSION_FACTORS,
    CO2_EMISSION_FACTORS,
    CH4_EMISSION_FACTORS,
    N2O_EMISSION_FACTORS,
    calculate_emission,
)


VEHICLE_TYPES = {"car", "motorcycle", "bus", "truck"}


def test_current_multi_pollutant_calculation_contract():
    result = calculate_emission(
        {"car": 10, "motorcycle": 20, "bus": 2, "truck": 1}
    )

    assert result == {
        "total_tsp_g_per_min": 2.24,
        "total_tsp_kg_per_hr": 0.1343,
        "total_nox_g_per_min": 34.79,
        "total_nox_kg_per_hr": 2.0871,
        "total_so2_g_per_min": 0.15,
        "total_so2_kg_per_hr": 0.009,
        "total_hc_g_per_min": 100.4,
        "total_hc_kg_per_hr": 6.0238,
        "total_co_g_per_min": 413.35,
        "total_co_kg_per_hr": 24.8009,
        "total_co2_g_per_min": 7256.0,
        "total_co2_kg_per_hr": 435.36,
        "total_ch4_g_per_min": 2.18,
        "total_ch4_kg_per_hr": 0.1306,
        "total_n2o_g_per_min": 0.06,
        "total_n2o_kg_per_hr": 0.0034,
        "breakdown": {
            "motorcycle": {
                "tsp_g_per_min": 1.54,
                "nox_g_per_min": 4.65,
                "so2_g_per_min": 0.03,
                "hc_g_per_min": 91.98,
                "co_g_per_min": 348.39,
                "co2_g_per_min": 2226.0,
                "ch4_g_per_min": 1.4,
                "n2o_g_per_min": 0.01,
            },
            "car": {
                "tsp_g_per_min": 0.02,
                "nox_g_per_min": 6.11,
                "so2_g_per_min": 0.04,
                "hc_g_per_min": 7.04,
                "co_g_per_min": 59.5,
                "co2_g_per_min": 2226.0,
                "ch4_g_per_min": 0.56,
                "n2o_g_per_min": 0.01,
            },
            "bus": {
                "tsp_g_per_min": 0.45,
                "nox_g_per_min": 16.02,
                "so2_g_per_min": 0.06,
                "hc_g_per_min": 0.92,
                "co_g_per_min": 3.64,
                "co2_g_per_min": 1536.0,
                "ch4_g_per_min": 0.14,
                "n2o_g_per_min": 0.02,
            },
            "truck": {
                "tsp_g_per_min": 0.23,
                "nox_g_per_min": 8.01,
                "so2_g_per_min": 0.03,
                "hc_g_per_min": 0.46,
                "co_g_per_min": 1.82,
                "co2_g_per_min": 768.0,
                "ch4_g_per_min": 0.07,
                "n2o_g_per_min": 0.01,
            },
        },
    }


def test_zero_and_missing_vehicle_counts_are_zero():
    result = calculate_emission({})

    assert result["total_tsp_g_per_min"] == 0.0
    assert result["total_nox_g_per_min"] == 0.0
    assert result["total_so2_g_per_min"] == 0.0
    assert result["total_hc_g_per_min"] == 0.0
    assert result["total_co_g_per_min"] == 0.0
    assert result["total_co2_g_per_min"] == 0.0
    assert result["total_ch4_g_per_min"] == 0.0
    assert result["total_n2o_g_per_min"] == 0.0
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
        ("tsp", TSP_EMISSION_FACTORS),
        ("nox", NOX_EMISSION_FACTORS),
        ("so2", SO2_EMISSION_FACTORS),
        ("hc", HC_EMISSION_FACTORS),
        ("co", CO_EMISSION_FACTORS),
        ("co2", CO2_EMISSION_FACTORS),
        ("ch4", CH4_EMISSION_FACTORS),
        ("n2o", N2O_EMISSION_FACTORS),
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
