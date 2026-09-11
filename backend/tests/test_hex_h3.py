from types import SimpleNamespace

from app.services.hex_h3 import (
    aggregate_cells,
    h3_boundary_geojson,
    h3_cell,
    in_bbox,
    quantile_breaks,
)


def _cell(hex_id, luas=1.0, poi=3, penduduk=100, score=55.0, label="Sedang"):
    return SimpleNamespace(
        hex_id=hex_id, luas_km2=luas, poi_total=poi, penduduk=penduduk,
        skor_total_ahp=score, klasifikasi_potensi=label,
    )


def test_h3_boundary_is_a_closed_geojson_ring():
    cell = h3_cell(110.37, -7.79, 8)
    ring = h3_boundary_geojson(cell)
    assert len(ring) == 7
    assert ring[0] == ring[-1]
    # GeoJSON axis order is [lon, lat]; the ring sits around the input point.
    assert all(109 < lon < 111 and -9 < lat < -6 for lon, lat in ring)


def test_in_bbox_accepts_inside_and_rejects_outside():
    bounds = (110.0, -8.0, 111.0, -7.0)
    assert in_bbox(110.5, -7.5, bounds)
    assert not in_bbox(112.0, -7.5, bounds)
    assert in_bbox(112.0, -7.5, None)


def test_quantile_breaks_are_strictly_increasing_min_to_max():
    breaks = quantile_breaks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert breaks is not None
    assert len(breaks) == 5
    assert breaks[0] == 1 and breaks[-1] == 10
    assert all(right > left for left, right in zip(breaks, breaks[1:]))


def test_quantile_breaks_none_when_flat_or_empty():
    assert quantile_breaks([]) is None
    assert quantile_breaks([7]) is None
    assert quantile_breaks([4, 4, 4]) is None


def test_quantile_breaks_stay_increasing_with_ties():
    breaks = quantile_breaks([0, 0, 0, 0, 100])
    assert breaks is not None
    assert all(right > left for left, right in zip(breaks, breaks[1:]))


def test_aggregate_cells_sums_and_area_weights():
    members = [(_cell(1, luas=1.0, poi=2, penduduk=10, score=20.0, label="Rendah"), 0.0, 0.0),
               (_cell(2, luas=3.0, poi=4, penduduk=30, score=60.0, label="Tinggi"), 0.0, 0.0)]
    aggregate = aggregate_cells(members, scores=None)
    assert aggregate["luas_km2"] == 4.0
    assert aggregate["poi_total"] == 6
    assert aggregate["penduduk"] == 40
    # Area-weighted mean: (1*20 + 3*60) / 4.
    assert aggregate["skor_total_ahp"] == 50.0
    assert aggregate["klasifikasi_potensi"] == "Tinggi"


def test_aggregate_cells_uses_live_scores_and_omits_unscored():
    members = [(_cell(1, luas=1.0), 0.0, 0.0), (_cell(2, luas=1.0), 0.0, 0.0)]
    scores = {1: {"skor_total_ahp": 80.0, "klasifikasi_potensi": "Sangat Tinggi"}, 2: {"skor_total_ahp": None}}
    aggregate = aggregate_cells(members, scores)
    assert aggregate["skor_total_ahp"] == 80.0
    assert aggregate["klasifikasi_potensi"] == "Sangat Tinggi"


def test_aggregate_cells_without_scored_members_returns_none_score():
    members = [(_cell(1), 0.0, 0.0)]
    aggregate = aggregate_cells(members, {1: {"skor_total_ahp": None}})
    assert aggregate["skor_total_ahp"] is None
