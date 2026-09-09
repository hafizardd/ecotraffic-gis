import pytest

from app.schemas.emission import EmissionSummaryResponse
from app.services.emission_aggregation import EMISSION_RATE_FIELDS


def test_summary_preserves_fractional_aggregated_vehicle_counts():
    response = EmissionSummaryResponse(
        total_cameras_active=1,
        **{field: 0.0 for field in EMISSION_RATE_FIELDS},
        by_vehicle={
            "car": 3.53254,
            "motorcycle": 0.11558,
            "bus": 0.85276,
            "truck": 0.39107,
        },
        last_updated=None,
    )

    assert response.by_vehicle.car == pytest.approx(3.53254)
    assert response.by_vehicle.motorcycle == pytest.approx(0.11558)
    assert response.by_vehicle.bus == pytest.approx(0.85276)
    assert response.by_vehicle.truck == pytest.approx(0.39107)
