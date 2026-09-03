import pytest

from app.services.tier2_emission_calculator import calculate_tier2_emissions


def test_motorcycle_co_uses_proposal_factor():
    result = calculate_tier2_emissions({"motorcycle": 200})
    assert result["totals_g_h"]["CO"] == 2800
    assert result["by_category_g_h"]["motorcycle"]["CO"] == 2800


def test_control_efficiency_reduces_emission_by_percentage():
    result = calculate_tier2_emissions({"motorcycle": 200}, control_efficiency=10)
    assert result["totals_g_h"]["CO"] == 2520
    assert result["correction"] == 0.9


@pytest.mark.parametrize("efficiency", [-1, 101, float("nan")])
def test_invalid_control_efficiency_is_rejected(efficiency):
    with pytest.raises(ValueError, match="control_efficiency"):
        calculate_tier2_emissions({}, control_efficiency=efficiency)


def test_all_categories_and_pollutants_are_present():
    result = calculate_tier2_emissions({})
    assert set(result["totals_g_h"]) == {"TSP", "NOx", "SO2", "HC", "CO", "CO2", "CH4", "N2O"}
    assert set(result["by_category_g_h"]) == {"motorcycle", "gasoline_car", "diesel_car", "bus", "truck"}
