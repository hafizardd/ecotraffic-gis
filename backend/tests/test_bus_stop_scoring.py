from types import SimpleNamespace

from app.services.bus_stop_scoring import BUS_STOP_COMPONENT_WEIGHTS, build_assessments
from app.services.survey_ahp import AHP_CONSISTENCY_RATIO, AHP_WEIGHTS, load_records


def test_ahp_weights_are_validated_and_ordered():
    assert abs(sum(AHP_WEIGHTS.values()) - 1) < 1e-9
    assert AHP_CONSISTENCY_RATIO < 0.1
    assert AHP_WEIGHTS["accessibility"] > AHP_WEIGHTS["condition"] > AHP_WEIGHTS["environment"]
    assert BUS_STOP_COMPONENT_WEIGHTS["accessibility"] == AHP_WEIGHTS["accessibility"]
    assert BUS_STOP_COMPONENT_WEIGHTS["facility"] == AHP_WEIGHTS["condition"]


def test_weighted_components_reproduce_workbook_total():
    records, report = load_records()
    assert report["matched"] == 64
    assert not report["unmatched_geo"]
    assert not report["beyond_tolerance"]
    for record in records:
        expected = (
            AHP_WEIGHTS["accessibility"] * record["accessibility_score_100"]
            + AHP_WEIGHTS["condition"] * record["condition_score_100"]
            + AHP_WEIGHTS["environment"] * record["environment_score_100"]
        )
        assert abs(expected - record["ahp_total_score"]) < 0.01


def test_build_assessments_prefers_imported_ahp_values():
    stops = [
        SimpleNamespace(source_id="a", ahp_total_score=76.66, ahp_classification="Tinggi", ahp_rank=1,
                        accessibility_score_100=100.0, condition_score_100=75.0, environment_score_100=42.0,
                        facility_score=None, environment_score=None),
        SimpleNamespace(source_id="b", ahp_total_score=None, ahp_classification=None, ahp_rank=None,
                        accessibility_score_100=None, condition_score_100=None, environment_score_100=None,
                        facility_score=5.0, environment_score=5.0),
    ]
    assessments = {a["source_id"]: a for a in build_assessments(stops, {"a": 999.0, "b": 1.0})}

    assert assessments["a"]["score"] == 76.66
    assert assessments["a"]["class"] == "Tinggi"
    # Lower score = higher intervention priority = lower rank number.
    assert assessments["b"]["rank"] == 1
    assert assessments["a"]["rank"] == 2
    assert assessments["b"]["score"] is not None
    assert assessments["b"]["method"] == "keyword"


def test_build_assessments_fallback_still_ranks_without_ahp():
    stops = [
        SimpleNamespace(source_id="a", ahp_total_score=None, ahp_classification=None, ahp_rank=None,
                        accessibility_score_100=None, condition_score_100=None, environment_score_100=None,
                        facility_score=5.0, environment_score=5.0),
        SimpleNamespace(source_id="b", ahp_total_score=None, ahp_classification=None, ahp_rank=None,
                        accessibility_score_100=None, condition_score_100=None, environment_score_100=None,
                        facility_score=1.0, environment_score=1.0),
    ]
    assessments = {a["source_id"]: a for a in build_assessments(stops, {"a": 10.0, "b": 0.0})}

    assert assessments["b"]["rank"] == 1
    assert assessments["a"]["rank"] == 2
    assert assessments["a"]["class"] is not None
    assert assessments["a"]["score"] > assessments["b"]["score"]
