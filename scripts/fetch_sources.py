"""Unduh sumber mentah untuk pipeline: geometri, PDF SSGI, dan tabel BPS 2022.

Semua berkas mendarat di data/sources/ dan tidak dikomit (lihat .gitignore).
Koneksi dipakai seperlunya: tiga unduhan kecil, sekali jalan.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from urllib.request import Request, urlretrieve

GEOMETRI_URL = (
    "https://raw.githubusercontent.com/eppofahmi/geojson-indonesia/"
    "master/kota/all_kabkota_ind.geojson"
)
SSGI_URL = (
    "https://repository.badankebijakan.kemkes.go.id/id/eprint/4855/3/"
    "Buku%20Saku%20SSGI%202022%20rev%20270123%20OK.pdf"
)
KAGGLE_DATASET = "ldausl/klasifikasi-tingkat-kemiskinan-di-indonesia"


def unduh(url: str, tujuan: Path) -> None:
    if tujuan.exists() and tujuan.stat().st_size > 0:
        print(f"ada, lewati: {tujuan.name}")
        return
    print(f"mengunduh {tujuan.name} ...")
    req = Request(url, headers={"User-Agent": "spatial-stats-id/0.1 (pendidikan)"})
    urlretrieve(req.full_url, tujuan)
    print(f"  selesai ({tujuan.stat().st_size / 1e6:.1f} MB)")


def utama() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", type=Path, default=Path("data/sources"))
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    unduh(GEOMETRI_URL, args.outdir / "all_kabkota_ind.geojson")
    unduh(SSGI_URL, args.outdir / "buku_saku_ssgi_2022.pdf")

    csv_tujuan = args.outdir / "indikator_bps_2022.csv"
    if not csv_tujuan.exists():
        import kagglehub

        jalur = Path(kagglehub.dataset_download(KAGGLE_DATASET))
        for f in jalur.rglob("*.csv"):
            shutil.copy(f, csv_tujuan)
            break
        print(f"kaggle CSV disalin: {csv_tujuan.name}")
    else:
        print(f"ada, lewati: {csv_tujuan.name}")

    print("\nLangkah berikutnya:")
    print("  python scripts/build_geodata.py data/sources/all_kabkota_ind.geojson")
    print("  python scripts/extract_ssgi.py data/sources/buku_saku_ssgi_2022.pdf -o data/ssgi_stunting_2022_raw.csv")
    print("  python scripts/build_indicators.py data/sources/indikator_bps_2022.csv data/ssgi_stunting_2022_raw.csv")


if __name__ == "__main__":
    utama()
