from app.schemas.segment_emission import SegmentEmissionMapItem, SegmentEmissionResponse
from app.api.routes.segment_emissions import _iso


def test_map_response_is_lightweight():
    item = SegmentEmissionMapItem(
        road_segment_id="segment-1", decision_score=0.73, priority="Very High",
        total_emission=12345.67, calculated_at="2026-09-03T10:00:00Z",
    )
    assert set(item.model_dump()) == {
        "road_segment_id", "decision_score", "priority", "total_emission",
        "calculated_at", "observed_at", "data_age_seconds", "freshness_status",
        "vehicle_count_semantics", "source_cameras",
    }


def test_geojson_temporal_fields_serialize_as_iso_strings_or_null():
    from datetime import datetime, timezone

    moment = datetime(2026, 9, 6, 13, 0, tzinfo=timezone.utc)
    assert _iso(moment) == "2026-09-06T13:00:00+00:00"
    assert _iso(None) is None
    assert isinstance(_iso(moment), str)
