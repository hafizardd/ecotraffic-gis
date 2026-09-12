from datetime import datetime, timedelta, timezone

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation


def test_plan_known_value_sample():
    start = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)
    observations = [
        SegmentTrafficObservation("a", "segment-001", "northbound", start, 60, {"motorcycle": 40}),
        SegmentTrafficObservation("b", "segment-001", "southbound", start, 60, {"motorcycle": 35}),
    ]
    result = calculate_segment_emission(observations, period_start=start, period_end=start + timedelta(minutes=1), road_length_km=0.8)
    assert result["volume_per_hour"]["motorcycle"] == 4500
    assert result["vkt_km_h"]["motorcycle"] == 3600
    assert result["emissions"]["by_category_g_h"]["motorcycle"]["CO"] == 50400
