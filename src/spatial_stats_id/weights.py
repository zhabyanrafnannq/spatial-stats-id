"""Matriks bobot spasial untuk kumpulan wilayah yang sedang dianalisis.

Tetangga Queen sudah dihitung dari geometri resolusi penuh (adjacency.json),
jadi runtime tidak butuh geopandas. Bobot jarak dihitung dari centroid
lintang-bujur dengan jarak haversine.
"""
from __future__ import annotations

import numpy as np
from libpysal.weights import W


def _haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    r = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def subset_tetangga(tetangga: dict[str, list[str]], ids: list[str]) -> dict[str, list[str]]:
    set_id = set(ids)
    return {k: [t for t in v if t in set_id] for k, v in tetangga.items() if k in set_id}


def bobot_queen(tetangga: dict[str, list[str]], ids: list[str]) -> W:
    """W dari tetangga Queen yang dibatasi ke wilayah berdata, terstandardisasi baris."""
    terbatas = subset_tetangga(tetangga, ids)
    neighbors = {k: terbatas[k] for k in ids}
    weights = {k: [1.0] * len(v) for k, v in neighbors.items()}
    w = W(neighbors=neighbors, weights=weights, id_order=ids, silence_warnings=True)
    w.transform = "r"
    return w


def bobot_jarak(latlon: dict[str, tuple[float, float]], ids: list[str], ambang_km: float = 150.0) -> W:
    """W distance-band terstandardisasi baris: bertetangga bila centroid terpisah kurang dari ambang km."""
    lat = np.array([latlon[k][0] for k in ids])
    lon = np.array([latlon[k][1] for k in ids])
    n = len(ids)
    neighbors: dict[str, list[str]] = {}
    weights: dict[str, list[float]] = {}
    for i in range(n):
        jarak = _haversine_km(lat[i], lon[i], lat, lon)
        terjang = [ids[j] for j in range(n) if j != i and jarak[j] <= ambang_km]
        neighbors[ids[i]] = terjang
        weights[ids[i]] = [1.0] * len(terjang)
    w = W(neighbors=neighbors, weights=weights, id_order=ids, silence_warnings=True)
    w.transform = "r"
    return w


def ringkas(w: W) -> dict:
    """Statistik ringkas bobot untuk pelaporan (isolates, rata-rata tetangga)."""
    n = len(w.id_order)
    n_tetangga = [len(w.neighbors[k]) for k in w.id_order]
    isolates = [k for k in w.id_order if len(w.neighbors[k]) == 0]
    return {
        "n": n,
        "rata_rata_tetangga": float(np.mean(n_tetangga)) if n else 0.0,
        "n_isolates": len(isolates),
        "isolates": isolates,
        "pasangan": sum(n_tetangga) // 2,
    }
