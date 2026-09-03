import pytest

from cv.proposal_emission_factors import (
    EMISSION_FACTORS,
    POLLUTANTS,
    VEHICLE_CATEGORIES,
    validate_emission_factors,
)
from cv.detector import DEFAULT_YOLO_CATEGORY_MAPPING


def test_proposal_factors_cover_all_canonical_categories_and_pollutants():
    assert tuple(EMISSION_FACTORS) == VEHICLE_CATEGORIES
    assert all(set(factors) == set(POLLUTANTS) for factors in EMISSION_FACTORS.values())


def test_proposal_factor_values_are_finite_and_non_negative():
    validate_emission_factors()
    assert EMISSION_FACTORS["motorcycle"]["CO"] == 14.0
    assert EMISSION_FACTORS["truck"]["NOx"] == 17.7


def test_missing_category_or_pollutant_is_rejected():
    missing_category = dict(EMISSION_FACTORS)
    missing_category.pop("truck")
    with pytest.raises(ValueError, match="vehicle categories"):
        validate_emission_factors(missing_category)

    missing_pollutant = {category: dict(values) for category, values in EMISSION_FACTORS.items()}
    missing_pollutant["bus"].pop("CO")
    with pytest.raises(ValueError, match="bus"):
        validate_emission_factors(missing_pollutant)


def test_default_yolo_mapping_assigns_car_to_gasoline_category():
    assert DEFAULT_YOLO_CATEGORY_MAPPING == {
        "motorcycle": "motorcycle",
        "car": "gasoline_car",
        "bus": "bus",
        "truck": "truck",
    }
