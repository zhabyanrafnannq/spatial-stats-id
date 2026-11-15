"""Pengujian matriks bobot spasial."""
from spatial_stats_id.weights import bobot_jarak, bobot_queen, ringkas, subset_tetangga

IDS = ["a", "b", "c", "d"]
TETANGGA = {"a": ["b", "c"], "b": ["a"], "c": ["a"], "d": []}


def test_bobot_queen_simetris_dan_terbatas():
    w = bobot_queen(TETANGGA, IDS)
    assert w.id_order == IDS
    for i in IDS:
        for j in w.neighbors[i]:
            assert i in w.neighbors[j], f"asimetri {i}-{j}"


def test_subset_tetangga_menggugurkan():
    terbatas = subset_tetangga(TETANGGA, ["a", "b"])
    assert terbatas == {"a": ["b"], "b": ["a"]}


def test_bobot_jarak_haversine():
    latlon = {
        "dekat1": (0.0, 110.0),
        "dekat2": (0.0, 110.5),
        "jauh": (0.0, 112.0),
        "sumbu": (-1.0, 110.0),
    }
    ids = ["dekat1", "dekat2", "jauh", "sumbu"]
    w = bobot_jarak(latlon, ids, ambang_km=60.0)
    assert w.neighbors["dekat1"] == ["dekat2"]  # 0,5 derajat ~ 56 km
    assert w.neighbors["jauh"] == []  # ~222 km
    assert w.neighbors["sumbu"] == []  # 1 derajat ~ 111 km


def test_bobot_jarak_ambang_melebar():
    latlon = {
        "dekat1": (0.0, 110.0),
        "dekat2": (0.0, 110.5),
        "jauh": (0.0, 112.0),
        "sumbu": (-1.0, 110.0),
    }
    ids = ["dekat1", "dekat2", "jauh", "sumbu"]
    w = bobot_jarak(latlon, ids, ambang_km=130.0)
    assert "jauh" not in w.neighbors["dekat1"]
    assert "sumbu" in w.neighbors["dekat1"]
    assert "sumbu" in w.neighbors["dekat2"]  # ~124 km


def test_ringkas_isolates():
    w = bobot_queen(TETANGGA, IDS)
    r = ringkas(w)
    assert r["n"] == 4 and r["n_isolates"] == 1 and r["isolates"] == ["d"]
    assert r["pasangan"] == 2
