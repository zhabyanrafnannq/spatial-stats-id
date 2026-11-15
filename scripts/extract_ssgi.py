"""Ekstrak prevalensi stunting kab/kota dari Buku Saku SSGI 2022 (Kemenkes).

Halaman stunting per provinsi menyajikan grafik batang: teks label dan nilai
dirotasi 90 derajat. pdfplumber dibaca level karakter, dikelompokkan per batang
berdasar posisi x, lalu dirangkai urutan baca (sort bottom menurun).

Label nama wilayah di buku terpotong sekitar 18 karakter; potongan itu
disambungkan ke nama lengkap pada tahap join (scripts/build_indicators.py).

Penggunaan:
    python scripts/extract_ssgi.py data/sources/buku_saku_ssgi_2022.pdf \
        -o data/ssgi_stunting_2022_raw.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pdfplumber

JUDUL = re.compile(r"PREVALENSI BALITA STUNTING.*DI PROVINSI ([A-Z .]+), SSGI")
NILAI = re.compile(r"(\d+\.\d+)$")


def kelompokkan_x(chars: list[dict], jarak: float = 5.0) -> list[list[dict]]:
    urut = sorted(chars, key=lambda c: (c["x0"] + c["x1"]) / 2)
    kel = [[urut[0]]]
    for sebelum, sesudah in zip(urut, urut[1:]):
        tengah_sblm = (sebelum["x0"] + sebelum["x1"]) / 2
        tengah_sdh = (sesudah["x0"] + sesudah["x1"]) / 2
        if tengah_sdh - tengah_sblm > jarak:
            kel.append([])
        kel[-1].append(sesudah)
    return kel


def baca_halaman(hal: pdfplumber.page.Page) -> tuple[str, list[dict]]:
    teks = (hal.extract_text() or "").replace("\n", " ")
    m = JUDUL.search(teks)
    if not m:
        return "", []
    provinsi = m.group(1).strip()

    rotasi = [c for c in hal.chars if not c.get("upright") and c["top"] > 95]
    if not rotasi:
        return provinsi, []

    batang, label_lepas = [], []
    for kel in kelompokkan_x(rotasi):
        s = "".join(c["text"] for c in sorted(kel, key=lambda c: -c["bottom"]))
        mv = NILAI.search(s)
        x = (kel[0]["x0"] + kel[0]["x1"]) / 2
        if mv:
            batang.append({"label": s[: mv.start()].strip(), "nilai": float(mv.group(1)), "x": x})
        elif s.strip():
            label_lepas.append({"label": s.strip(), "x": x})

    # baris label yang wrap terpisah dari angkanya: sambungkan ke batang terdekat
    for b in batang:
        if not b["label"] and label_lepas:
            kandidat = min(label_lepas, key=lambda L: abs(L["x"] - b["x"]))
            if abs(kandidat["x"] - b["x"]) < 6:
                b["label"] = kandidat["label"]
                label_lepas.remove(kandidat)
    return provinsi, batang


def utama() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf", type=Path, help="path Buku Saku SSGI 2022")
    ap.add_argument("-o", "--out", type=Path, default=Path("data/ssgi_stunting_2022_raw.csv"))
    args = ap.parse_args()

    baris = []
    with pdfplumber.open(args.pdf) as pdf:
        for i, hal in enumerate(pdf.pages):
            provinsi, batang = baca_halaman(hal)
            if not provinsi:
                continue
            n_label_kosong = sum(1 for b in batang if not b["label"])
            print(f"hal {i+1:3d} {provinsi:30s} batang={len(batang):2d} label_kosong={n_label_kosong}")
            for b in batang:
                baris.append({
                    "provinsi_buku": provinsi,
                    "label_buku": b["label"],
                    "stunting": b["nilai"],
                    "halaman": i + 1,
                })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        f.write("provinsi_buku,label_buku,stunting,halaman\n")
        for r in baris:
            f.write(f"{r['provinsi_buku']},{r['label_buku']},{r['stunting']},{r['halaman']}\n")
    print(f"\n{len(baris)} baris -> {args.out}")


if __name__ == "__main__":
    utama()
