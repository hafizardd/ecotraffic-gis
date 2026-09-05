from cv.emission_factors import calculate_emission


def test_public_vehicle_contract_is_four_categories():
    from cv.proposal_emission_factors import VEHICLE_CATEGORIES

    assert VEHICLE_CATEGORIES == ("car", "motorcycle", "bus", "truck")


def test_car_contributes_to_camera_emissions():
    result = calculate_emission({"car": 2})
    assert result["total_co2_g_per_min"] > 0
    assert result["breakdown"]["car"]["co2_g_per_min"] > 0
