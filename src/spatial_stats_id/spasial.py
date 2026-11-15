"""Statistik spasial: Moran's I global, LISA, dan regresi spasial dasar.

Permutasi diset satu seed agar hasil dashboard dapat direproduksi.
"""
from __future__ import annotations

import numpy as np
from esda.moran import Moran, Moran_Local

LABEL_KUADRAN = {
    0: "Tidak signifikan",
    1: "High-High",
    2: "Low-High",
    3: "Low-Low",
    4: "High-Low",
}

WARNA_KUADRAN = {
    "High-High": "#b3322d",
    "Low-Low": "#2c5d8f",
    "Low-High": "#d9a13c",
    "High-Low": "#8a8a5c",
    "Tidak signifikan": "#d8d5cd",
}

SEED = 42


def _y_vector(nilai: list[float], w) -> np.ndarray:
    """Vektor y dalam urutan id_order bobot, NaN digugurkan lebih awal."""
    y = np.asarray(nilai, dtype=float)
    if np.isnan(y).any():
        raise ValueError("nilai NaN harus digugurkan sebelum analisis")
    return y


def moran_global(nilai: list[float], w, permutasi: int = 999) -> dict:
    y = _y_vector(nilai, w)
    np.random.seed(SEED)
    mi = Moran(y, w, permutations=permutasi)
    return {
        "I": float(mi.I),
        "E_I": float(mi.EI),
        "z_sim": float(mi.z_sim),
        "p_sim": float(mi.p_sim),
        "permutasi": permutasi,
        "n": len(y),
    }


def lisa(nilai: list[float], w, permutasi: int = 999, alpha: float = 0.05) -> list[dict]:
    """Klasifikasi kuadran LISA per wilayah, dalam urutan w.id_order."""
    y = _y_vector(nilai, w)
    np.random.seed(SEED)
    ml = Moran_Local(y, w, permutations=permutasi)
    lag = np.asarray(w.sparse @ ml.z).ravel()
    hasil = []
    for i, kode in enumerate(w.id_order):
        p = float(ml.p_sim[i])
        sig = bool(np.isfinite(p) and p < alpha)
        q = int(ml.q[i]) if sig else 0
        hasil.append({
            "kode": kode,
            "z": float(ml.z[i]),
            "lag": float(lag[i]),
            "p_sim": p,
            "kuadran": LABEL_KUADRAN[q],
            "signifikan": sig,
        })
    return hasil


def moran_scatter(nilai: list[float], w) -> list[dict]:
    """Pasangan (z, lag) ternormalisasi untuk plot Moran, urutan id_order."""
    y = _y_vector(nilai, w)
    z = (y - y.mean()) / y.std(ddof=0)
    lag = np.asarray(w.sparse @ z).ravel()
    return [{"kode": k, "z": float(z[i]), "lag": float(lag[i])} for i, k in enumerate(w.id_order)]


def regresi_spasial(y, X: list[list[float]], w, nama_y: str, nama_x: list[str]) -> dict:
    """OLS, ML_Lag, dan ML_Error; y dan X harus bebas NaN, urutan id_order.

    Uji LR dependensi spasial dihitung manual dari selisih log-likelihood
    terhadap OLS (2*(logll_ML - logll_OLS), df=1) agar tidak bergantung pada
    atribut diagnostik yang berbeda antar versi spreg.
    """
    from scipy.stats import chi2
    from spreg import ML_Error, ML_Lag, OLS

    yv = np.asarray(y, dtype=float).reshape(-1, 1)
    Xm = np.asarray(X, dtype=float)
    if Xm.ndim == 1:
        Xm = Xm.reshape(-1, 1)

    ols = OLS(yv, Xm, w=w, name_y=nama_y, name_x=nama_x, name_w="bobot", white_test=False)
    ml_lag = ML_Lag(yv, Xm, w=w, name_y=nama_y, name_x=nama_x, method="full")
    ml_err = ML_Error(yv, Xm, w=w, name_y=nama_y, name_x=nama_x, method="full")

    def koef(model, term: list[str]) -> list[dict]:
        stat = getattr(model, "z_stat", None) or getattr(model, "t_stat", None)
        out = []
        for i, nm in enumerate(term):
            baris = {"istilah": nm, "koef": float(model.betas[i][0]), "std_err": None, "p": None}
            if stat is not None and i < len(stat):
                baris["std_err"] = float(stat[i][0])
                baris["p"] = float(stat[i][1])
            out.append(baris)
        return out

    def uji_lr(logll_m: float) -> tuple[float, float]:
        lr = float(2.0 * (logll_m - ols.logll))
        return lr, float(chi2.sf(lr, 1))

    lag_lr, lag_lr_p = uji_lr(ml_lag.logll)
    err_lr, err_lr_p = uji_lr(ml_err.logll)
    z_lag = getattr(ml_lag, "z_stat", None)
    bp = getattr(ols, "breusch_pagan", None)

    term_ols = ["CONST"] + nama_x
    term_ml = ["CONST"] + nama_x + ["W_" + nama_y]

    return {
        "n": int(len(yv)),
        "ols": {
            "r2": float(ols.r2),
            "r2_aj": float(ols.ar2),
            "koef": koef(ols, term_ols),
            "bp_p": float(bp["pvalue"]) if isinstance(bp, dict) and "pvalue" in bp else None,
        },
        "lag": {
            "rho": float(ml_lag.rho),
            "rho_p": float(z_lag[-1][1]) if z_lag is not None else None,
            "pseudo_r2": float(ml_lag.pr2) if hasattr(ml_lag, "pr2") else None,
            "lr_stat": lag_lr,
            "lr_p": lag_lr_p,
            "koef": koef(ml_lag, term_ml),
        },
        "error": {
            "lambda": float(getattr(ml_err, "lam", getattr(ml_err, "lambda", np.nan))),
            "lr_stat": err_lr,
            "lr_p": err_lr_p,
        },
    }
