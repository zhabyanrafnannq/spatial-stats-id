"""Pemuatan artefak data yang dikomit ke repositori.

Artefak dibangun oleh scripts/build_geodata.py dan scripts/build_indicators.py;
dashboard hanya membaca, tanpa akses jaringan.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

ARTEFAK = {
    "geometri": "kabkota.geojson",
    "tetangga": "adjacency.json",
    "kemiskinan": "indikator_kemiskinan_2022.csv",
    "stunting": "indikator_stunting_2022.csv",
}


def dir_data() -> Path:
    """Cari folder data: variabel lingkungan, root repo, lalu cwd."""
    kandidat = []
    if env := os.environ.get("SPATIAL_STATS_ID_DATA"):
        kandidat.append(Path(env))
    root = Path(__file__).resolve().parents[2]
    kandidat.append(root / "data" / "processed")
    kandidat.append(Path.cwd() / "data" / "processed")
    for k in kandidat:
        if (k / ARTEFAK["geometri"]).exists():
            return k
    raise FileNotFoundError(
        "data/processed tidak ditemukan; jalankan scripts/build_geodata.py dulu"
    )


def path_artefak(nama: str) -> Path:
    return dir_data() / ARTEFAK[nama]


@lru_cache(maxsize=None)
def muat_geometri() -> tuple[list[dict], dict[str, list[str]], pd.DataFrame]:
    """(fitur geojson, tetangga Queen, master wilayah berurutan sesuai geojson)."""
    gj = json.loads(path_artefak("geometri").read_text(encoding="utf-8"))
    tetangga = json.loads(path_artefak("tetangga").read_text(encoding="utf-8"))
    baris = []
    for f in gj["features"]:
        p = f["properties"]
        baris.append({
            "kode": p["kode"],
            "nama": p["nama"],
            "tipe": p["tipe"],
            "provinsi": p["provinsi"],
            "stem": p["stem"],
            "lat": p["lat"],
            "lon": p["lon"],
        })
    master = pd.DataFrame(baris).astype({"kode": "string"})
    tetangga = {k: list(v) for k, v in tetangga.items()}
    return gj["features"], tetangga, master


@lru_cache(maxsize=None)
def muat_indikator(nama: str) -> pd.DataFrame:
    df = pd.read_csv(path_artefak(nama), dtype={"kode": "string"})
    return df


def gabung_wilayah(nama_indikator: str) -> pd.DataFrame:
    """Master wilayah + indikator pilihan, urutan mengikuti geojson."""
    _, _, master = muat_geometri()
    ind = muat_indikator(nama_indikator)
    kolom_nilai = [c for c in ind.columns if c not in ("kode", "provinsi", "kabkota")]
    gab = master.merge(ind, on="kode", how="left", suffixes=("", "_ind"))
    return gab, kolom_nilai
