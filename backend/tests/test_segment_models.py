from app.models import RoadSegment, SegmentEmission


def test_segment_models_are_registered_with_expected_tables():
    assert RoadSegment.__tablename__ == "road_segments"
    assert SegmentEmission.__tablename__ == "segment_emissions"
    assert "road_segment_id" in SegmentEmission.__table__.c
