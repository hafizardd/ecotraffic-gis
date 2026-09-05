from cv.proposal_emission_factors import normalize_vehicle_counts
from cv.emission_factors import calculate_emission


def test_fuel_specific_cars_share_public_car_category():
    assert normalize_vehicle_counts({"gasoline_car": 2, "diesel_car": 3}) == {
        "car": 5.0, "motorcycle": 0.0, "bus": 0.0, "truck": 0.0,
    }


def test_car_contributes_to_camera_emissions():
    result = calculate_emission({"car": 2})
    assert result["total_co2_g_per_min"] > 0
    assert result["breakdown"]["car"]["co2_g_per_min"] > 0
