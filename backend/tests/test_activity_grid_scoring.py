from types import SimpleNamespace

from app.services.bus_stop_scoring import build_assessments
from app.services.classification import quintile_classify
from app.services.hex_activity_scoring import recompute_hour_scores


def _hex(hex_id):
    return SimpleNamespace(hex_id=hex_id, norm_poi=50.0, norm_penduduk=50.0)


def test_recompute_flags_unmapped_hexes_with_nearest_neighbour_fallback():
    scores = recompute_hour_scores(
        [_hex(1), _hex(2), _hex(3)],
        {1: 100.0},
        {1: (0.0, 0.0), 2: (0.01, 0.0), 3: (1.0, 0.0)},
    )
    assert scores[1]["data_status"] == "live"
    assert scores[2]["data_status"] == "fallback"
    assert scores[2]["fallback_from"] == 1
    assert scores[2]["skor_total_ahp"] is not None
    assert scores[3]["data_status"] == "fallback"
    assert scores[3]["fallback_from"] == 1
    assert scores[3]["ranking"] is None
    # A borrowed cell still carries a tier label (from its own score, not a rank).
    assert scores[3]["klasifikasi_potensi"] is not None


def test_recompute_without_centroids_keeps_unmapped_hexes_no_data():
    scores = recompute_hour_scores([_hex(1), _hex(2)], {1: 50.0})
    assert scores[1]["data_status"] == "live"
    assert scores[2]["data_status"] == "no_data"
    assert scores[2]["skor_total_ahp"] is None


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
