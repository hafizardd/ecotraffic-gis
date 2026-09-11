import copy
import warnings
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SAWarning
from sqlalchemy.sql import compiler as sql_compiler

import app.api.routes.bangjo as bangjo
from app.api.routes.bangjo import _parse_answer
from app.services.bangjo_context import build_context


def test_parse_answer_strips_code_fences_and_prose():
    answer = _parse_answer('```json\n{"summary": "x", "drivers": ["a"]}\n```')
    assert answer["summary"] == "x"
    assert answer["drivers"] == ["a"]


def test_parse_answer_recovers_trailing_commas():
    answer = _parse_answer('{"summary": "x", "drivers": ["a",],}')
    assert answer == {"summary": "x", "asi_category": "", "recommendation": "", "drivers": ["a"], "evidence": []}


def test_parse_answer_normalizes_smart_quotes():
    assert _parse_answer('{\u201csummary\u201d: \u201cx\u201d}')["summary"] == "x"


def test_parse_answer_falls_back_to_single_quoted_fields():
    answer = _parse_answer("{'summary': 'halo', 'drivers': ['a','b']}")
    assert answer["summary"] == "halo"
    assert answer["drivers"] == ["a", "b"]


def test_parse_answer_extracts_fields_without_braces():
    answer = _parse_answer('summary: halo\ndrivers: ["a"]\nevidence: ["e1", "e2"]')
    assert answer["summary"] == "halo"
    assert answer["drivers"] == ["a"]
    assert answer["evidence"] == ["e1", "e2"]


def test_parse_answer_raises_when_no_summary_present():
    with pytest.raises(ValueError):
        _parse_answer("hello, I cannot help with that")


def test_parse_answer_rejects_prose_only_free_model_reply():
    with pytest.raises(ValueError):
        _parse_answer("Tentu, berikut analisis singkat koridor ini berdasarkan konteks yang tersedia.")


class _FakeResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self._content = content
        self.request = None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise bangjo.httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return {"choices": [{"message": {"content": self._content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


class _FakeClient:
    def __init__(self, contents):
        self._contents = list(contents)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append(json)
        return _FakeResponse(200, self._contents.pop(0))


@pytest.mark.asyncio
async def test_ask_llm_retries_once_when_first_response_is_unparseable(monkeypatch):
    client = _FakeClient(["Tentu, ini bukan JSON.", '{"summary": "ok", "drivers": ["a"]}'])
    monkeypatch.setattr(bangjo.settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(bangjo.httpx, "AsyncClient", lambda *args, **kwargs: client)

    answer = await bangjo._ask_llm("halo", {}, [])

    assert answer["source"] == "llm"
    assert answer["summary"] == "ok"
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_ask_llm_falls_back_with_reason_when_retry_also_fails(monkeypatch):
    client = _FakeClient(["prose one", "prose two"])
    monkeypatch.setattr(bangjo.settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(bangjo.httpx, "AsyncClient", lambda *args, **kwargs: client)
    context = {"segment": {"name": "Jalan", "road_segment_id": "SEG-1"},
               "activity_potential": {}, "bus_stops": [], "coverage_gap": False}

    answer = await bangjo._ask_llm("halo", context, [])

    assert answer["source"] == "fallback"
    assert answer["fallback_reason"] == "parse_error"
    assert len(client.calls) == 2


class _FakeResult:
    def __init__(self, rows=None, value=None):
        self._rows = rows or []
        self._value = value

    def first(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar(self):
        return self._value


class _FakeDB:
    def __init__(self, results):
        self._results = list(results)
        self.statements = []

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_build_context_bus_stops_have_no_cartesian_product_warning():
    segment = SimpleNamespace(road_segment_id="SEG-0001", name="Jalan Kenari", length_km=1.0)
    stop = SimpleNamespace(source_id="STOP-1", title="Halte", intervention_class="Shift",
                           intervention_rank=1, accessibility_score=0.5, facility_score=0.5,
                           environment_score=0.5)
    db = _FakeDB([
        _FakeResult(rows=[(segment, None)]),
        _FakeResult(rows=[]),
        _FakeResult(rows=[(stop, 123.456)]),
        _FakeResult(value=0),
    ])

    context = await build_context(db, "SEG-0001")

    assert context["bus_stops"] == [{
        "source_id": "STOP-1", "title": "Halte", "intervention_class": "Shift", "intervention_rank": 1,
        "accessibility_score": 0.5, "facility_score": 0.5, "environment_score": 0.5,
        "distance_to_segment_m": 123.5,
    }]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for statement in db.statements:
            statement.compile(dialect=postgresql.dialect(), linting=sql_compiler.FROM_LINTING)
    cartesian = [w for w in caught
                 if issubclass(w.category, SAWarning) and "cartesian" in str(w.message).lower()]
    assert not cartesian, f"unexpected cartesian product warning: {[str(w.message) for w in cartesian]}"


@pytest.mark.asyncio
async def test_resolve_segment_aggregates_same_name_chunks():
    db = _FakeDB([_FakeResult(rows=[("SEG-0001", "Jalan Kenari"), ("SEG-0002", "Jalan Kenari"),
                                    ("SEG-0003", "Jalan Kenari")])])
    ids, candidates = await bangjo._resolve_segment(db, "Jalan Kenari emisinya seberapa?")

    assert ids == ["SEG-0001", "SEG-0002", "SEG-0003"]
    assert candidates == []


@pytest.mark.asyncio
async def test_resolve_segment_dedupes_candidates_when_ambiguous():
    db = _FakeDB([_FakeResult(rows=[("SEG-0001", "Jalan Malioboro"), ("SEG-0002", "Jalan Malioboro"),
                                    ("SEG-0003", "Jalan Solo")])])
    ids, candidates = await bangjo._resolve_segment(db, "jalan")

    assert ids is None
    assert [candidate["name"] for candidate in candidates] == ["Jalan Malioboro", "Jalan Solo"]
    assert candidates[0]["count"] == 2


@pytest.mark.asyncio
async def test_resolve_segment_falls_back_to_token_overlap():
    db = _FakeDB([_FakeResult(rows=[("SEG-0001", "Jalan Kyai Mojo"), ("SEG-0002", "Jalan Kenari")])])
    ids, candidates = await bangjo._resolve_segment(db, "kyai mojo emisinya?")

    assert ids == ["SEG-0001"]
    assert candidates == []


def test_merge_contexts_aggregates_chunks():
    base = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "segment": {"road_segment_id": "SEG-0001", "name": "Jalan Kenari", "length_km": 0.5,
                    "activity_class": "Sedang", "activity_score": 2.0, "pollutant_totals": {"co2": 100.0},
                    "data_source": "snapshot", "observed_at": None},
        "activity_potential": {"hex_count": 1, "hex_ids": [1], "avg_skor_total_ahp": 2.0,
                               "max_skor_total_ahp": 2.0, "klasifikasi_potensi": ["Sedang"],
                               "dominant_poi_categories": [{"category": "kantor", "count": 3}]},
        "bus_stops": [], "coverage_gap": False,
    }
    other = copy.deepcopy(base)
    other["segment"].update(road_segment_id="SEG-0002", length_km=0.7, activity_score=3.0,
                            activity_class="Tinggi", pollutant_totals={"co2": 50.0})
    other["activity_potential"].update(hex_ids=[2], avg_skor_total_ahp=3.0)
    other["coverage_gap"] = True

    merged = bangjo._merge_contexts([base, other])

    assert merged["segment"]["chunk_count"] == 2
    assert merged["segment"]["road_segment_ids"] == ["SEG-0001", "SEG-0002"]
    assert merged["segment"]["length_km"] == 1.2
    assert merged["segment"]["activity_class"] == "Tinggi"
    assert merged["segment"]["pollutant_totals"] == {"co2": 150.0}
    assert merged["activity_potential"]["hex_ids"] == [1, 2]
    assert merged["activity_potential"]["avg_skor_total_ahp"] == 2.5
    assert merged["activity_potential"]["dominant_poi_categories"] == [{"category": "kantor", "count": 6}]
    assert merged["coverage_gap"] is True


def test_merge_contexts_rolls_up_stop_assessment_and_intervention_priority():
    base = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "segment": {"road_segment_id": "SEG-0001", "name": "Jalan Kenari", "length_km": 0.5,
                    "activity_class": "Tinggi", "activity_score": 3.0, "pollutant_totals": None,
                    "data_source": None, "observed_at": None},
        "activity_potential": {"hex_count": 0, "hex_ids": [], "avg_skor_total_ahp": None,
                               "max_skor_total_ahp": None, "klasifikasi_potensi": None,
                               "dominant_poi_categories": []},
        "bus_stops": [], "coverage_gap": False,
        "stop_assessment": {"count": 1, "scored_count": 1, "class_counts": {"Rendah": 1},
                            "weak_stop_count": 1, "min_ahp_total_score": 40.0, "avg_ahp_total_score": 40.0},
        "intervention_hint": "improve_existing_stop",
    }
    other = copy.deepcopy(base)
    other["segment"].update(road_segment_id="SEG-0002")
    other["coverage_gap"] = True
    other["intervention_hint"] = "add_new_stop"
    other["stop_assessment"].update(count=2, scored_count=0, class_counts={"Rendah": 2},
                                    weak_stop_count=1, min_ahp_total_score=None, avg_ahp_total_score=None)

    merged = bangjo._merge_contexts([base, other])

    assert merged["intervention_hint"] == "add_new_stop"
    assert merged["stop_assessment"]["count"] == 3
    assert merged["stop_assessment"]["class_counts"] == {"Rendah": 3}
    assert merged["stop_assessment"]["weak_stop_count"] == 2
    assert merged["stop_assessment"]["min_ahp_total_score"] == 40.0

