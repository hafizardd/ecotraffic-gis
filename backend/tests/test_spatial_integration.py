import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from cv.detector import DEFAULT_MODEL_PATH
from app.services.spatial_integration import (
    POI_CATEGORY_WEIGHTS,
    _normalize,
    compute_all_spatial_criteria,
    score_survey_description,
)


def test_survey_description_only_scores_on_clear_evidence():
    result = score_survey_description("Halte dengan shelter, bangku, dan penerangan yang baik")
    assert result["facility"] is not None
    assert result["facility"] >= 1
    assert result["environment"] is None


def test_survey_description_ambiguous_evidence_is_unavailable():
    result = score_survey_description("Observasi dilakukan pada sore hari")
    assert all(value is None for value in result.values())


def test_normalize_inverts_k3():
    assert _normalize(10, (10, 20), invert=True) == pytest.approx(1.0)
    assert _normalize(20, (10, 20), invert=True) == pytest.approx(0.0)
    assert _normalize(15, (10, 20), invert=False) == pytest.approx(0.5)


def test_normalize_missing_stays_missing():
    assert _normalize(None, (10, 20)) is None
    assert _normalize(15, None) is None


def test_poi_weights_are_versioned_and_explicit():
    assert "Pendidikan" in POI_CATEGORY_WEIGHTS
    assert "Peribadatan" in POI_CATEGORY_WEIGHTS


def test_yolo_default_is_yolo11n():
    assert Settings.model_fields["YOLO_MODEL_PATH"].default == "yolo/yolo11n.pt"
    assert DEFAULT_MODEL_PATH.endswith("yolo11n.pt")


def test_spatial_queries_use_segment_column_not_ewkb_literal():
    class _Result:
        def scalars(self):
            return self

        def all(self):
            return []

        def scalar_one_or_none(self):
            return None

    class _DB:
        def __init__(self):
            self.statements = []

        def execute(self, statement, *args, **kwargs):
            self.statements.append(statement)
            return _Result()

    segment = SimpleNamespace(id=uuid.uuid4(), road_segment_id="SEG-0001", length_km=1.0)
    db = _DB()
    result = compute_all_spatial_criteria(db, segment)

    assert result["component_status"]["K4"] == "complete"
    compiled = [str(s.compile(dialect=postgresql.dialect())) for s in db.statements]
    assert compiled, "expected at least one spatial query"
    for sql in compiled:
        assert "ST_GeogFromText" not in sql, "segment geometry must not be bound as EWKB text literal"
        assert "road_segments" in sql, "spatial query must reference the road_segments table"

