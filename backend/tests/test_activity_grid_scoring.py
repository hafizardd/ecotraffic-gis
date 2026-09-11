from types import SimpleNamespace

from app.services.bus_stop_scoring import build_assessments
from app.services.classification import quintile_classify


def test_quintile_matches_excel_choose_roundup():
    assert quintile_classify(1, 378) == (1, "Sangat Tinggi")
    assert quintile_classify(76, 378) == (2, "Tinggi")
    assert quintile_classify(152, 378) == (3, "Sedang")
    assert quintile_classify(303, 378) == (5, "Sangat Rendah")
    assert quintile_classify(378, 378) == (5, "Sangat Rendah")


def test_build_assessments_ranks_and_classifies():
    stops = [
        SimpleNamespace(source_id="a", facility_score=5.0, environment_score=5.0),
        SimpleNamespace(source_id="b", facility_score=1.0, environment_score=1.0),
        SimpleNamespace(source_id="c", facility_score=None, environment_score=None),
    ]
    assessments = {a["source_id"]: a for a in build_assessments(stops, {"a": 10.0, "b": 0.0, "c": 0.0})}
    # Intervention rank is ascending by score: lowest score = top priority.
    assert assessments["c"]["rank"] == 1
    assert assessments["b"]["rank"] == 2
    assert assessments["a"]["rank"] == 3 and assessments["a"]["class"] == "Tinggi"
    assert assessments["a"]["score"] > assessments["b"]["score"] > assessments["c"]["score"]
