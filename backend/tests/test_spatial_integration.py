import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from cv.detector import DEFAULT_MODEL_PATH
from app.services.spatial_integration import (
    POI_CATEGORY_WEIGHTS,
    compute_population_context,
    resolve_primary_hex,
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


def test_poi_weights_are_versioned_and_explicit():
    assert "Pendidikan" in POI_CATEGORY_WEIGHTS
    assert "Peribadatan" in POI_CATEGORY_WEIGHTS


def test_yolo_default_is_yolo11n():
    assert Settings.model_fields["YOLO_MODEL_PATH"].default == "yolo/best30.pt"
    assert DEFAULT_MODEL_PATH.endswith("yolo11n.pt")


def test_population_context_queries_use_segment_column_not_ewkb_literal():
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
    assert compute_population_context(db, segment) is None

    compiled = [str(s.compile(dialect=postgresql.dialect())) for s in db.statements]
    assert compiled, "expected at least one spatial query"
    for sql in compiled:
        assert "ST_GeogFromText" not in sql, "segment geometry must not be bound as EWKB text literal"
        assert "road_segments" in sql, "spatial query must reference the road_segments table"


class _AsyncResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _AsyncDB:
    def __init__(self, value):
        self.statements = []
        self._value = value

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        return _AsyncResult(self._value)


@pytest.mark.asyncio
async def test_resolve_primary_hex_returns_intersecting_hex():
    cell = SimpleNamespace(hex_id=7)
    db = _AsyncDB(cell)
    assert await resolve_primary_hex(db, SimpleNamespace(id=uuid.uuid4())) is cell

    sql = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "ST_Intersects" in sql
    assert "ST_Intersection" in sql
    assert "ST_Length" in sql
    assert "DESC" in sql.upper()
    assert "road_segments" in sql


@pytest.mark.asyncio
async def test_resolve_primary_hex_none_when_segment_uncovered():
    assert await resolve_primary_hex(_AsyncDB(None), SimpleNamespace(id=uuid.uuid4())) is None
