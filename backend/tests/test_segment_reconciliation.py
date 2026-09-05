from datetime import datetime, timezone

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation


def test_category_pollutants_reconcile_to_pollutant_totals():
    captured_at = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)
    observation = SegmentTrafficObservation(
        "camera-a", "segment-1", "northbound", captured_at, 60,
        {"motorcycle": 40, "car": 10, "bus": 1, "truck": 2},
    )
    result = calculate_segment_emission(
        [observation], period_start=captured_at,
        period_end=captured_at.replace(minute=1), road_length_km=0.8,
    )
    breakdown = result["emissions"]["by_category_g_h"]
    totals = result["emissions"]["totals_g_h"]
    for pollutant, total in totals.items():
        assert sum(values[pollutant] for values in breakdown.values()) == total
