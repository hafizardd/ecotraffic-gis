import pytest

from app.api.routes.bangjo import _parse_answer


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
