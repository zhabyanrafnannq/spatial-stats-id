"""Bangun artefak geodata dari GeoJSON mirror batas kab/kota (turunan shapefile BIG).

Keluaran (dikomit ke repo, dibaca dashboard):
    data/processed/kabkota.geojson   geometri tersederhana + nama + centroid
    data/processed/adjacency.json    tetangga Queen dari geometri resolusi penuh

Simplifikasi hanya untuk tampilan peta; tetangga tetap dihitung dari geometri
penuh agar klaster spasial tidak terpengaruh artefak simplifikasi.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shapely.geometry import shape
from shapely.strtree import STRtree

from spatial_stats_id.nama import TYPO_STEM, pisah_tipe, rapikan_spasi

TEBAL_SIMPLIFIKASI = 0.002  # derajat, sekitar 200 m di ekuator
DESAIMAL = 5


def bulatkan(x):
    if isinstance(x, float):
        return round(x, DESAIMAL)
    if isinstance(x, list):
        return [bulatkan(v) for v in x]
    return x


def utama() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("geojson", type=Path, help="GeoJSON mirror kab/kota resolusi penuh")
    ap.add_argument("--outdir", type=Path, default=Path("data/processed"))
    args = ap.parse_args()

    gj = json.loads(args.geojson.read_text(encoding="utf-8"))
    feats = gj["features"]
    print(f"fitur mentah: {len(feats)}")

    geoms = [shape(f["geometry"]) for f in feats]
    prop = []
    for f in feats:
        p = f["properties"]
        tipe, stem = pisah_tipe(p["alt_name"])
        stem = TYPO_STEM.get(stem, stem)
        nama_mentah = rapikan_spasi(p["name"]).upper()
        if tipe == "kota":
            _, stem_name = pisah_tipe(nama_mentah)
        else:
            # kabupaten: 'Kota' di awal nama (Kotabaru) adalah bagian nama, bukan tipe
            stem_name = nama_mentah
            if stem_name.startswith("KABUPATEN "):
                stem_name = stem_name[len("KABUPATEN "):].strip()
        stem_name = TYPO_STEM.get(stem_name, stem_name)
        assert stem == stem_name, f"alt_name vs name tidak cocok: {p['alt_name']} / {p['name']}"
        prop.append({
            "kode": p["province_id"] + p["kabkot_id"],
            "tipe": tipe,
            "stem": stem,
            "provinsi": rapikan_spasi(p["prov_name"]).upper(),
            "lat": p["latitude"],
            "lon": p["longitude"],
        })

    kode_set = {p["kode"] for p in prop}
    assert len(kode_set) == len(prop), "ada kode wilayah duplikat"

    tree = STRtree(geoms)
    tetangga = {p["kode"]: set() for p in prop}
    n_pasangan = 0
    for i, g in enumerate(geoms):
        for j in tree.query(g, predicate="intersects"):
            if j > i and geoms[j].intersects(g):
                tetangga[prop[i]["kode"]].add(prop[j]["kode"])
                tetangga[prop[j]["kode"]].add(prop[i]["kode"])
                n_pasangan += 1

    fitur_baru = []
    for p, g in zip(prop, geoms):
        g_sederhana = g.simplify(TEBAL_SIMPLIFIKASI, preserve_topology=True)
        if g_sederhana.is_empty:
            g_sederhana = g
        fitur_baru.append({
            "type": "Feature",
            "id": p["kode"],
            "properties": {
                "kode": p["kode"],
                "nama": ("Kota " if p["tipe"] == "kota" else "Kabupaten ") + p["stem"].title(),
                "tipe": p["tipe"],
                "provinsi": p["provinsi"],
                "stem": p["stem"],
                "lat": p["lat"],
                "lon": p["lon"],
            },
            "geometry": {**g_sederhana.__geo_interface__, "coordinates": bulatkan(g_sederhana.__geo_interface__["coordinates"])},
        })

    args.outdir.mkdir(parents=True, exist_ok=True)
    out_gj = args.outdir / "kabkota.geojson"
    out_gj.write_text(json.dumps({"type": "FeatureCollection", "features": fitur_baru},
                                 ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    out_adj = args.outdir / "adjacency.json"
    tetangga_bersih = {k: sorted(v) for k, v in sorted(tetangga.items())}
    out_adj.write_text(json.dumps(tetangga_bersih, separators=(",", ":")), encoding="utf-8")

    pulau = [k for k, v in tetangga_bersih.items() if not v]
    print(f"pasangan bertetangga: {n_pasangan}")
    print(f"wilayah tanpa tetangga (pulau): {len(pulau)} -> {pulau[:8]}")
    print(f"kabkota.geojson: {out_gj.stat().st_size / 1e6:.2f} MB | adjacency.json: {out_adj.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    utama()
