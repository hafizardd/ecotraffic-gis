from types import SimpleNamespace

from app.services.bus_stop_scoring import build_assessments
from app.services.classification import quintile_classify
from app.services.hex_activity_scoring import recompute_hour_scores


def _hex(hex_id, volume_mean=None):
    return SimpleNamespace(hex_id=hex_id, norm_poi=50.0, norm_penduduk=50.0, volume_mean=volume_mean)


def test_recompute_labels_observed_and_baseline_grids_on_one_rank_scale():
    # Hex 2 has an hourly volume; 1 and 3 fall back to their own volume_mean.
    # All three share one ranking and one quintile scale (the Excel model).
    scores = recompute_hour_scores(
        [_hex(1, volume_mean=10.0), _hex(2, volume_mean=20.0), _hex(3, volume_mean=30.0)],
        {2: 100.0},
    )
    assert scores[2]["data_status"] == "live"
    assert scores[1]["data_status"] == "fallback"
    assert scores[3]["data_status"] == "fallback"
    assert sorted(scores[i]["ranking"] for i in (1, 2, 3)) == [1, 2, 3]
    # Every grid - observed or estimated - gets the class of its rank.
    for hex_id in (1, 2, 3):
        rank = scores[hex_id]["ranking"]
        assert scores[hex_id]["klasifikasi_potensi"] == quintile_classify(rank, 3)[1]
        assert scores[hex_id]["ranking_total"] == 3


def test_recompute_borrows_nearest_observed_volume():
    hexes = [_hex(1, volume_mean=10.0), _hex(2, volume_mean=20.0), _hex(3, volume_mean=30.0)]
    centroids = {1: (0.0, 0.0), 2: (0.01, 0.0), 3: (1.0, 0.0)}
    scores = recompute_hour_scores(hexes, {1: 10.0, 3: 30.0}, centroids)
    assert scores[1]["data_status"] == "live"
    assert scores[3]["data_status"] == "live"
    assert scores[2]["data_status"] == "fallback"
    assert scores[2]["fallback_from"] == 1
    assert scores[2]["ranking"] is not None


def test_recompute_baseline_scoring_needs_no_centroids():
    scores = recompute_hour_scores([_hex(1, volume_mean=10.0), _hex(2, volume_mean=20.0)], {1: 50.0})
    assert scores[1]["data_status"] == "live"
    assert scores[2]["data_status"] == "fallback"
    assert scores[2]["ranking"] is not None


def test_recompute_without_volume_or_baseline_stays_no_data():
    scores = recompute_hour_scores([_hex(1, volume_mean=50.0), _hex(2)], {1: 50.0})
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
