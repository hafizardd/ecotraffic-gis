import pytest

from app.services.spatial_criteria import derive_spatial_criteria


def test_spatial_criteria_preserves_metadata_and_inverts_bus_accessibility():
    result = derive_spatial_criteria(
        [{"K3": 10, "K4": 1, "K5": 100}, {"K3": 20, "K4": 3, "K5": 200}],
        source="survey-2026", units={"K3": "stops", "K4": "poi/km2", "K5": "people"}, buffer_distance_m=300,
    )
    assert result[0]["normalized"]["K3"] == 1
    assert result[1]["normalized"]["K3"] == 0
    assert result[0]["metadata"]["buffer_distance_m"] == 300


def test_missing_spatial_values_are_not_treated_as_zero():
    with pytest.raises(ValueError, match="missing spatial criteria"):
        derive_spatial_criteria(
            [{"K3": None, "K4": 1, "K5": 2}], source="source",
            units={"K3": "stops", "K4": "poi/km2", "K5": "people"},
        )
