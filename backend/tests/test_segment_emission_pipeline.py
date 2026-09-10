from datetime import datetime, timedelta, timezone

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation


def test_pipeline_aggregates_before_calculating_emissions():
    start = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)
    observations = [SegmentTrafficObservation("camera-a", "segment-1", "northbound", start, 60, {"motorcycle": 40})]
    result = calculate_segment_emission(observations, period_start=start, period_end=start + timedelta(minutes=1), road_length_km=0.8)
    assert result["volume_per_hour"]["motorcycle"] == 2400
    assert result["emissions"]["totals_g_h"]
    assert tuple(result["provenance"]["source_cameras"]) == ("camera-a",)
    for deprecated in ("raw_criteria", "normalized_criteria", "decision_score", "priority", "spatial_criteria_status", "spatial_details"):
        assert deprecated not in result
