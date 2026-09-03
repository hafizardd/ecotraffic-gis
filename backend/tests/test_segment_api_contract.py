from app.schemas.segment_emission import SegmentEmissionMapItem, SegmentEmissionResponse


def test_map_response_is_lightweight():
    item = SegmentEmissionMapItem(
        road_segment_id="segment-1", decision_score=0.73, priority="Very High",
        total_emission=12345.67, calculated_at="2026-09-03T10:00:00Z",
    )
    assert set(item.model_dump()) == {"road_segment_id", "decision_score", "priority", "total_emission", "calculated_at"}
