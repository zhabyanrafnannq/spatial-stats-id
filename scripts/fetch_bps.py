"""Klien WebAPI BPS untuk memperbarui indikator (kunci API gratis: webapi.bps.go.id).

Skrip ini TIDAK dipakai dashboard: dashboard membaca snapshot yang dikomit agar
tetap stabil dan tanpa kunci di cloud. Gunakan skrip ini untuk menyegarkan
snapshot ketika BPS menerbitkan angka baru.

Contoh:
    export BPS_API_KEY=xxxx
    python scripts/fetch_bps.py --var 912 --th 2024 --out data/bps_cache/kemiskinan_2024.csv

Struktur respons mengikuti dokumentasi WebAPI v1 (webapi.bps.go.id/documentation);
vervar memuat pasangan kode wilayah (val) dan nama (label).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path

import requests

URL_DASAR = "https://webapi.bps.go.id"


def url_data(api_key: str, domain: str, var: str, th: str) -> str:
    return f"{URL_DASAR}/{api_key}/json/data/{domain}/var/{var}/th/{th}"


def ambil_data_variabel(api_key: str, domain: str, var: str, th: str, cache: Path) -> list[dict]:
    """Ambil satu variabel x satu tahun, kembalikan baris tidy (kode, wilayah, nilai)."""
    file_cache = cache / f"{domain}_{var}_{th}.json"
    file_cache.parent.mkdir(parents=True, exist_ok=True)
    if file_cache.exists():
        payload = json.loads(file_cache.read_text(encoding="utf-8"))
    else:
        resp = requests.get(url_data(api_key, domain, var, th), timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        file_cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        time.sleep(1.0)  # hormati server sumber

    vervar = {str(v["val"]): v["label"] for v in payload.get("vervar", [])}
    baris = []
    for isi in payload.get("datacontent", []):
        kode = str(isi.get("ver", ""))
        nilai = isi.get("nilai") if isi.get("nilai") is not None else isi.get("data")
        if kode == "" or nilai in ("-", "", None):
            continue
        baris.append({"kode": kode, "wilayah": vervar.get(kode, ""), "nilai": str(nilai)})
    return baris


def utama() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--var", required=True, help="id variabel WebAPI BPS")
    ap.add_argument("--th", required=True, help="tahun data")
    ap.add_argument("--domain", default="0000", help="domain wilayah (0000 = seluruh)")
    ap.add_argument("--out", type=Path, required=True, help="CSV tidy keluaran")
    ap.add_argument("--api-key", default=None, help="bawaan dari env BPS_API_KEY")
    args = ap.parse_args()

    api_key = args.api_key or os.environ.get("BPS_API_KEY")
    if not api_key:
        raise SystemExit("Kunci API belum ada: set BPS_API_KEY atau --api-key (daftar gratis di webapi.bps.go.id)")

    baris = ambil_data_variabel(api_key, args.domain, args.var, args.th, Path("data/bps_cache"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kode", "wilayah", "nilai"])
        for b in baris:
            w.writerow([b["kode"], b["wilayah"], b["nilai"]])
    print(f"{len(baris)} baris -> {args.out}")


if __name__ == "__main__":
    utama()
