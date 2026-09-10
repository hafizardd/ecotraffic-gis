from datetime import datetime, time, timezone

import pytest
from pydantic import ValidationError

from data_pipeline.activities.schemas import SemanticExtraction, SurveyKnowledgeRecord
from data_pipeline.activities.transforms import (
    deterministic_semantic,
    extract_observation_time,
    mark_duplicates,
    merge_semantic,
    parse_coordinates,
    parse_created_at,
    parse_media,
    resolve_stop_entities,
    semantic_validation_warnings,
    time_period_for,
)


def test_coordinate_parsing_uses_geojson_order_and_keeps_invalid_as_invalid():
    assert parse_coordinates("[110.375, -7.787]")[:3] == (110.375, -7.787, True)
    longitude, latitude, valid, error = parse_coordinates("[999, -7.787]")
    assert (longitude, latitude, valid) == (None, None, False)
    assert error


def test_timestamp_parsing_converts_utc_to_asia_jakarta():
    utc_value, local_value, error = parse_created_at("2026-08-27T05:40:32.699Z")
    assert error is None
    assert utc_value.isoformat() == "2026-08-27T05:40:32.699000+00:00"
    assert local_value.isoformat() == "2026-08-27T12:40:32.699000+07:00"


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(4, "early_morning"), (7, "morning"), (11, "midday"), (14, "afternoon"), (18, "evening"), (23, "night"), (2, "night")],
)
def test_time_period_boundaries(hour, expected):
    assert time_period_for(time(hour, 0)) == expected


def test_observation_time_without_date_is_not_converted_to_permanent_or_fabricated_datetime():
    parsed = extract_observation_time(
        "Observasi dilakukan sekitar pukul 12.32 WIB.",
        created_at_local=datetime(2026, 8, 27, 12, 40, tzinfo=timezone.utc),
    )
    assert parsed["observed_time"] == time(12, 32)
    assert parsed["observed_date"] is None
    assert parsed["observed_at"] is None
    assert parsed["observed_time_source"] == "description_explicit_time"
    assert parsed["time_period"] == "midday"


def test_created_at_fallback_is_explicit_and_low_confidence():
    created = datetime(2026, 8, 27, 12, 40, tzinfo=timezone.utc)
    parsed = extract_observation_time("Tidak ada jam observasi.", created_at_local=created, use_created_at_fallback=True)
    assert parsed["observed_at"] == created
    assert parsed["observed_time_source"] == "created_at_fallback"
    assert parsed["observed_time_confidence"] < 0.5


def test_media_parser_splits_image_and_video_urls():
    result = parse_media('["https://example.test/a.jpg", "https://example.test/b.mp4"]')
    assert result["media_valid"] is True
    assert result["image_count"] == 1
    assert result["video_count"] == 1
    assert parse_media("not-json")["media_valid"] is False


def _clean_row(observation_id, source_id, description, longitude, latitude):
    return {
        "observation_id": observation_id,
        "source_activity_id": source_id,
        "title_raw": "HALTE TJ CONTOH",
        "description_raw": description,
        "description_normalized": description,
        "coordinates_valid": True,
        "longitude": longitude,
        "latitude": latitude,
    }


def test_duplicate_detection_marks_content_duplicates_without_deleting_observations():
    rows = [
        _clean_row("obs-1", "source-1", "Deskripsi sama", 110.0, -7.0),
        _clean_row("obs-2", "source-2", "Deskripsi sama", 110.1, -7.1),
    ]
    mark_duplicates(rows)
    assert len(rows) == 2
    assert {row["duplicate_status"] for row in rows} == {"content_duplicate"}
    assert rows[0]["duplicate_group_id"] == rows[1]["duplicate_group_id"]


def test_entity_resolution_merges_nearby_same_name_but_splits_distant_coordinates():
    rows = [
        _clean_row("obs-1", "source-1", "A", 110.3750, -7.7870),
        _clean_row("obs-2", "source-2", "B", 110.3752, -7.7871),
        _clean_row("obs-3", "source-3", "C", 110.3900, -7.8000),
    ]
    resolve_stop_entities(rows, distance_threshold_m=150)
    assert rows[0]["stop_id"] == rows[1]["stop_id"]
    assert rows[2]["stop_id"] != rows[0]["stop_id"]
    assert all(row["entity_resolution_status"] == "split_same_name_distant_coordinates" for row in rows)


def test_unknown_is_not_false_for_unmentioned_facilities():
    result = deterministic_semantic("Halte terlihat ramai pada sore hari.")
    assert result.facilities.has_wifi is None
    assert result.facilities.has_seating is None
    assert result.accessibility.wheelchair_access is None


def test_generic_stop_function_is_not_mislabeled_as_observed_boarding():
    result = deterministic_semantic("Halte masih berfungsi sebagai titik naik dan turun penumpang Trans Jogja.")
    assert result.usage.boarding_activity is None


def test_nearby_school_extraction_stops_before_sentence_connector():
    result = deterministic_semantic(
        "Halte ini berada tepat di depan SMPN 5 Yogyakarta dan pada saat pengamatan terlihat ramai."
    )
    assert result.environment.nearby_places == ["SMPN 5 Yogyakarta"]


def test_schema_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        SemanticExtraction(confidence={"usage.passenger_level": 1.1})


def test_evidence_validation_reports_supported_value_without_evidence():
    extraction = SemanticExtraction.model_validate({"usage": {"passenger_level": "high"}})
    assert "missing evidence for usage.passenger_level" in semantic_validation_warnings(extraction)


def test_llm_recommendation_tags_are_recomputed_from_validated_facts():
    base = SemanticExtraction()
    enrichment = SemanticExtraction.model_validate({
        "accessibility": {"wheelchair_access": True},
        "recommendation_tags": ["invented_final_score"],
        "evidence": {"accessibility.wheelchair_access": "ramah kursi roda"},
        "confidence": {"accessibility.wheelchair_access": 0.9},
    })
    merged = merge_semantic(base, enrichment)
    assert merged.recommendation_tags == ["wheelchair_friendly"]


def test_knowledge_schema_rejects_coordinate_flag_mismatch():
    payload = {
        "knowledge_id": "knowledge-1", "source_activity_id": "source-1", "observation_id": "obs-1",
        "entity_resolution_confidence": 0, "entity_resolution_status": "unresolved",
        "latitude": None, "longitude": None, "coordinates_valid": True,
        "usage": {}, "facilities": {}, "accessibility": {}, "condition": {}, "environment": {},
        "issues": [], "strengths": [], "weaknesses": [], "recommendation_tags": [], "evidence": {}, "confidence": {},
        "title_raw": "x", "title_normalized": "X", "description_raw": "x", "description_normalized": "x",
        "image_urls": [], "video_urls": [], "image_count": 0, "video_count": 0, "media_valid": True,
        "duplicate_status": "unique",
        "provenance": {
            "source_file": "raw/activities_raw.csv", "source_row": 2, "processed_at": "2026-01-01T00:00:00Z",
            "extraction_provider": "openrouter", "extraction_model": "test", "extraction_status": "deterministic_only",
        },
    }
    with pytest.raises(ValidationError):
        SurveyKnowledgeRecord.model_validate(payload)
