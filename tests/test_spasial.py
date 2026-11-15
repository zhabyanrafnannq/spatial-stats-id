"""Pengujian statistik spasial pada data sintetis dengan pola diketahui."""
import numpy as np

from spatial_stats_id import spasial
from spatial_stats_id.weights import bobot_queen


def grid_9x9():
    """Grid 9x9, tetangga Queen; id diurutkan baris per baris."""
    n = 9
    ids = [f"{r}_{c}" for r in range(n) for c in range(n)]
    neigh = {}
    for r in range(n):
        for c in range(n):
            k = f"{r}_{c}"
            neigh[k] = [
                f"{r + dr}_{c + dc}"
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
                if 0 <= r + dr < n and 0 <=c + dc < n
            ]
    return ids, bobot_queen(neigh, ids)


def test_moran_global_data_mengelompok():
    ids, w = grid_9x9()
    # dua baris atas bernilai tinggi, tiga baris bawah rendah: autocorrelasi positif kuat
    y = [10.0 if int(k.split("_")[0]) < 2 else 1.0 for k in ids]
    hasil = spasial.moran_global(y, w, permutasi=199)
    assert hasil["I"] > 0.5
    assert hasil["p_sim"] <= 0.01


def test_moran_global_data_acak_dekat_nol():
    ids, w = grid_9x9()
    rng = np.random.default_rng(7)
    y = rng.normal(size=len(ids)).tolist()
    hasil = spasial.moran_global(y, w, permutasi=199)
    assert abs(hasil["I"]) < 0.2


def test_lisa_kuadran_ada_hh_dan_ll():
    ids, w = grid_9x9()
    # gradien utara-selatan: utara tinggi, selatan rendah
    y = [max(10.0 - 1.3 * int(k.split("_")[0]), 0.5) for k in ids]
    hasil = spasial.lisa(y, w, permutasi=999, alpha=0.05)
    kuadran = {h["kode"]: h["kuadran"] for h in hasil}
    assert kuadran["1_1"] == "High-High"
    assert "Low-Low" in set(kuadran.values())
    assert sum(1 for v in kuadran.values() if v == "High-High") >= 4


def test_moran_scatter_z_bermean_nol():
    ids, w = grid_9x9()
    y = np.arange(len(ids), dtype=float)
    pts = spasial.moran_scatter(y.tolist(), w)
    z = np.array([p["z"] for p in pts])
    assert abs(z.mean()) < 1e-9
    assert abs(z.std()) - 1 < 1e-9


def test_regresi_spasial_mengambil_rho():
    from scipy.sparse import eye as speye
    from scipy.sparse.linalg import spsolve

    ids, w = grid_9x9()
    rng = np.random.default_rng(11)
    x = rng.normal(size=len(ids))
    rho_asli = 0.4
    W = w.sparse.astype(float)
    eps = rng.normal(scale=0.3, size=len(ids))
    y = spsolve((speye(len(ids), format="csr") - rho_asli * W).tocsr(), 2.0 * x + eps)
    r = spasial.regresi_spasial(y.tolist(), x.tolist(), w, "y", ["x"])
    assert 0.15 < r["lag"]["rho"] < 0.65
    assert r["lag"]["lr_p"] < 0.05
    assert r["ols"]["koef"][1]["koef"] > 1.0
    assert r["ols"]["bp_p"] is not None
