def test_emission_factor_contract_can_be_imported():
    from cv.proposal_emission_factors import EMISSION_FACTORS, VEHICLE_CATEGORIES

    assert set(VEHICLE_CATEGORIES) == set(EMISSION_FACTORS)
    assert "car" in EMISSION_FACTORS
