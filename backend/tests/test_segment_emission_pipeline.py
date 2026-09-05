from datetime import datetime, timedelta, timezone

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation


def test_pipeline_aggregates_before_calculating_emissions_and_marks_spatial_pending():
    start = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)
    observations = [SegmentTrafficObservation("camera-a", "segment-1", "northbound", start, 60, {"motorcycle": 40})]
    result = calculate_segment_emission(observations, period_start=start, period_end=start + timedelta(minutes=1), road_length_km=0.8)
    assert result["volume_per_hour"]["motorcycle"] == 2400
    assert result["spatial_criteria_status"] == "pending"


def test_pipeline_calculates_complete_teds():
    start = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)
    observation = SegmentTrafficObservation("camera-a", "segment-1", "northbound", start, 60, {"motorcycle": 40})
    ranges = {key: (0, 100) for key in ("K1", "K2", "K3", "K4", "K5")}
    result = calculate_segment_emission(observation.__class__.__mro__ and [observation], period_start=start, period_end=start + timedelta(minutes=1), road_length_km=0.8, spatial_criteria={"K3": 10, "K4": 20, "K5": 30}, criterion_ranges=ranges)
    assert 0 <= result["decision_score"] <= 1
    assert result["priority"]
