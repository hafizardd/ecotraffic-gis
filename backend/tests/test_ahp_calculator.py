import pytest

from app.services.ahp_calculator import (
    PAIRWISE_MATRIX, calculate_weights, classify_priority, decision_score,
    normalize_criteria, validate_ahp_consistency,
)


def test_revised_weights_and_consistency_match_plan():
    weights = calculate_weights()
    assert weights["K1"] == pytest.approx(0.3601472448)
    assert weights["K5"] == pytest.approx(0.0395872422)
    assert sum(weights.values()) == pytest.approx(1.0)
    assert validate_ahp_consistency()["cr"] == pytest.approx(0.027242864, abs=1e-5)


def test_k3_is_inverse_while_direct_criteria_increase():
    ranges = {criterion: (1, 10) for criterion in ("K1", "K2", "K3", "K4", "K5")}
    low = normalize_criteria({"K1": 1, "K2": 1, "K3": 10, "K4": 1, "K5": 1}, ranges)
    high = normalize_criteria({"K1": 10, "K2": 10, "K3": 1, "K4": 10, "K5": 10}, ranges)
    assert low["K3"] == 0
    assert high["K3"] == 1


def test_priority_boundaries_are_lower_inclusive_and_one_is_critical():
    assert classify_priority(0.20) == "Moderate"
    assert classify_priority(0.40) == "High"
    assert classify_priority(0.60) == "Very High"
    assert classify_priority(0.80) == "Critical"
    assert classify_priority(1.0) == "Critical"


def test_score_is_clamped():
    assert decision_score({criterion: 2 for criterion in ("K1", "K2", "K3", "K4", "K5")}) == 1
