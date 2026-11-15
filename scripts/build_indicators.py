"""Gabungkan indikator BPS 2022 dan SSGI 2022 ke master wilayah berkode BPS.

Masukan:
    data/processed/kabkota.geojson          master nama + kode (dari build_geodata.py)
    CSV indikator BPS kab/kota 2022         argumen 1
    data/ssgi_stunting_2022_raw.csv         argumen 2 (hasil extract_ssgi.py)

Keluaran (dikomit, dibaca dashboard):
    data/processed/indikator_kemiskinan_2022.csv
    data/processed/indikator_stunting_2022.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from spatial_stats_id.nama import (
    cocok_stem,
    normal_provinsi,
    pisah_tipe,
    rapikan_spasi,
    TYPO_STEM,
)

# Label buku yang memakai nama lama/berbeda dari master dipetakan manual ke
# stem resmi. Kunci: (provinsi, label_buku) atau (provinsi, label_buku, nilai)
# bila satu label dipakai dua batang berbeda.
OVERRIDES_STUNTING = {
    ("MALUKU", "Kab. Kepulauan Tanimbar"): "MALUKU TENGGARA BARAT",
    ("MALUKU", "Kab. Kepulauan Kei"): "MALUKU TENGGARA",
    ("SULAWESI UTARA", "Kab. Sangihe Talaud"): "KEPULAUAN SANGIHE",
    ("SULAWESI BARAT", "Kab. Pasangkayu"): "MAMUJU UTARA",
    ("SULAWESI SELATAN", "Kab. Selayar"): "KEPULAUAN SELAYAR",
    ("SULAWESI UTARA", "Kota Mobagu"): "KOTAMOBAGU",
    ("JAWA TIMUR", "Kab. Malang=Kepanjen"): "MALANG",
    ("KALIMANTAN SELATAN", "Kota Baru"): "KOTABARU",
    # Buku salah menulis dua batang dengan label sama; Puncak Jaya 42,5
    # terkonfirmasi dari Rembuk Stunting Papua Tengah (SSGI 2022).
    ("PAPUA", "Kab. Puncak Jaya", 42.5): "PUNCAK JAYA",
    ("PAPUA", "Kab. Puncak Jaya", 42.0): "PUNCAK",
}

# Tabel BPS masih memakai nama lama: Kab. Pontianak berganti nama Kab. Mempawah (2013).
OVERRIDES_KEMISKINAN = {
    ("KALIMANTAN BARAT", "Pontianak"): "MEMPAWAH",
}

AWALAN_Tipe = ("KAB.", "KABUPATEN", "KOTA")

KOLOM_KEMISKINAN = [
    ("kemiskinan_p0", "Persentase Penduduk Miskin (P0) Menurut Kabupaten/Kota (Persen)"),
    ("rls", "Rata-rata Lama Sekolah Penduduk 15+ (Tahun)"),
    ("pengeluaran_kapita", "Pengeluaran per Kapita Disesuaikan (Ribu Rupiah/Orang/Tahun)"),
    ("ipm", "Indeks Pembangunan Manusia"),
    ("uhh", "Umur Harapan Hidup (Tahun)"),
    ("sanitasi_layak", "Persentase rumah tangga yang memiliki akses terhadap sanitasi layak"),
    ("air_layak", "Persentase rumah tangga yang memiliki akses terhadap air minum layak"),
    ("tpt", "Tingkat Pengangguran Terbuka"),
    ("tpak", "Tingkat Partisipasi Angkatan Kerja"),
    ("pdrb_konstan", "PDRB atas Dasar Harga Konstan menurut Pengeluaran (Rupiah)"),
]


def muat_master(path: Path) -> list[dict]:
    gj = json.loads(path.read_text(encoding="utf-8"))
    return [{
        "kode": f["properties"]["kode"],
        "provinsi": f["properties"]["provinsi"],
        "tipe": f["properties"]["tipe"],
        "stem": f["properties"]["stem"],
        "nama": f["properties"]["nama"],
    } for f in gj["features"]]


def stem_per_grup(master: list[dict]) -> dict[tuple[str, str], list[str]]:
    kandidat: dict[tuple[str, str], list[str]] = {}
    for m in master:
        kandidat.setdefault((m["provinsi"], m["tipe"]), []).append(m["stem"])
    return kandidat


def cari_kode(prov: str, tipe: str, stem: str, nama_raw: str, grup: dict) -> tuple[str | None, str]:
    """Empat tahap: tipe hasil parsing, nama mentah sebagai kabupaten
    (kasus 'Kota Baru' = Kotabaru), tipe lain (kasus 'Kab. Ternate' = kota),
    lalu tipe lain dengan nama mentah."""
    percobaan = (
        (tipe, stem, "parse"),
        ("kabupaten", nama_raw, "kab_mentah"),
        ("kabupaten" if tipe == "kota" else "kota", stem, "tipe_lain"),
        ("kabupaten" if tipe == "kota" else "kota", nama_raw, "tipe_lain_mentah"),
    )
    for t, s, alasan in percobaan:
        s_akhir = TYPO_STEM.get(s, s)
        stem_cocok, jenis = cocok_stem(s_akhir, grup.get((prov, t), []))
        if stem_cocok:
            kode = next(m["kode"] for m in MASTER
                        if m["provinsi"] == prov and m["tipe"] == t and m["stem"] == stem_cocok)
            return kode, f"{alasan}/{jenis}"
    return None, "tidak_ada"


MASTER: list[dict] = []


def utama() -> None:
    global MASTER
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kemiskinan", type=Path, help="CSV indikator BPS 2022")
    ap.add_argument("ssgi", type=Path, help="CSV hasil ekstraksi SSGI")
    ap.add_argument("--outdir", type=Path, default=Path("data/processed"))
    args = ap.parse_args()

    MASTER = muat_master(Path("data/processed/kabkota.geojson"))
    master_by_kode = {m["kode"]: m for m in MASTER}
    grup = stem_per_grup(MASTER)

    # --- kemiskinan BPS 2022 ---
    tak_cocok_kem, pemetaan_kem = [], {}
    with args.kemiskinan.open(encoding="utf-8-sig") as f:
        baris_kem = list(csv.DictReader(f))
    for r in baris_kem:
        prov = normal_provinsi(r["Provinsi"])
        nama = rapikan_spasi(r["Kab/Kota"].replace("*", ""))
        tipe, stem = pisah_tipe(nama)
        override = OVERRIDES_KEMISKINAN.get((prov, nama))
        if override:
            k = next((m["kode"] for m in MASTER
                      if m["provinsi"] == prov and m["stem"] == override), None)
            alasan = "override"
        else:
            k, alasan = cari_kode(prov, tipe, stem, nama.upper(), grup)
        if k:
            if k in pemetaan_kem:
                print(f"  GANDA kemiskinan: {k} ({master_by_kode[k]['nama']})")
            pemetaan_kem[k] = r
        else:
            tak_cocok_kem.append((prov, nama, alasan))
    print(f"kemiskinan: {len(pemetaan_kem)}/{len(MASTER)} wilayah terpetakan")
    for x in tak_cocok_kem:
        print(f"  TAK COCOK kemiskinan: {x}")

    # --- stunting SSGI 2022 ---
    tak_cocok_stu, pemetaan_stu, bar_agregat = [], {}, []
    with args.ssgi.open(encoding="utf-8") as f:
        baris_stu = list(csv.DictReader(f))
    for r in baris_stu:
        prov = normal_provinsi(r["provinsi_buku"])
        label = r["label_buku"].strip()
        tipe, stem = pisah_tipe(label)
        # batang agregat provinsi: label tanpa awalan tipe dan sama dengan provinsi
        if not label.upper().startswith(AWALAN_Tipe) and normal_provinsi(label) == prov:
            bar_agregat.append((prov, float(r["stunting"])))
            continue
        nilai = float(r["stunting"])
        k = None
        if (prov, label) in OVERRIDES_STUNTING:
            stem_full = OVERRIDES_STUNTING[(prov, label)]
            k = next((m["kode"] for m in MASTER
                      if m["provinsi"] == prov and m["stem"] == stem_full), None)
        if k is None and (prov, label, nilai) in OVERRIDES_STUNTING:
            stem_full = OVERRIDES_STUNTING[(prov, label, nilai)]
            k = next((m["kode"] for m in MASTER
                      if m["provinsi"] == prov and m["stem"] == stem_full), None)
        if k is None:
            k, alasan = cari_kode(prov, tipe, stem, label.upper(), grup)
            if not k:
                tak_cocok_stu.append((prov, label, alasan))
        if k:
            if k in pemetaan_stu:
                print(f"  GANDA stunting: {k} ({master_by_kode[k]['nama']})")
            pemetaan_stu[k] = nilai
    print(f"stunting: {len(pemetaan_stu)}/{len(MASTER)} wilayah terpetakan | bar agregat provinsi: {len(bar_agregat)}")
    for x in tak_cocok_stu:
        print(f"  TAK COCOK stunting: {x}")
    print("  bar agregat provinsi (validasi vs publikasi provinsi):")
    for p, v in bar_agregat:
        print(f"    {p:30s} {v}")

    args.outdir.mkdir(parents=True, exist_ok=True)

    out_kem = args.outdir / "indikator_kemiskinan_2022.csv"
    with out_kem.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kode", "provinsi", "kabkota"] + [c[0] for c in KOLOM_KEMISKINAN])
        for k, r in pemetaan_kem.items():
            m = master_by_kode[k]
            w.writerow([k, m["provinsi"], m["nama"]]
                       + [rapikan_spasi(r[c[1]]).replace(" ", "") or "" for c in KOLOM_KEMISKINAN])

    out_stu = args.outdir / "indikator_stunting_2022.csv"
    with out_stu.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kode", "provinsi", "kabkota", "stunting"])
        for k in sorted(pemetaan_stu):
            m = master_by_kode[k]
            w.writerow([k, m["provinsi"], m["nama"], pemetaan_stu[k]])

    print(f"\n{out_kem} ({out_kem.stat().st_size / 1e3:.0f} kB) | {out_stu} ({out_stu.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    utama()
