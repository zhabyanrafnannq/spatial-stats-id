"""Pengujian klien WebAPI BPS dengan payload tiruan (tanpa jaringan)."""
import json

import pytest

from scripts.fetch_bps import ambil_data_variabel, url_data

PAYLOAD = {
    "status": "OK",
    "vervar": [
        {"val": 1101, "label": "Simeulue"},
        {"val": 1102, "label": "Aceh Singkil"},
    ],
    "turvar": [],
    "datacontent": [
        {"ver": "1101", "nilai": "18.98"},
        {"ver": "1102", "nilai": "-"},
        {"ver": "9999", "nilai": "5.0"},
    ],
}


def test_url_data_bentuk_webapi_v1():
    assert url_data("KUNCI", "0000", "912", "2024") == (
        "https://webapi.bps.go.id/KUNCI/json/data/0000/var/912/th/2024"
    )


def test_ambil_data_variabel_tidy_dan_cache(tmp_path, monkeypatch):
    class RespTiruan:
        def raise_for_status(self):
            return None

        def json(self):
            return PAYLOAD

    dipanggil = []

    def get_tiruan(url, timeout):
        dipanggil.append(url)
        return RespTiruan()

    import scripts.fetch_bps as fb

    monkeypatch.setattr(fb.requests, "get", get_tiruan)
    cache = tmp_path / "cache"

    baris = ambil_data_variabel("KUNCI", "0000", "912", "2024", cache)
    assert dipanggil and "webapi.bps.go.id" in dipanggil[0]
    # baris kosong ('-') digugurkan; kode yang tak dikenal kosongkan nama
    assert baris == [
        {"kode": "1101", "wilayah": "Simeulue", "nilai": "18.98"},
        {"kode": "9999", "wilayah": "", "nilai": "5.0"},
    ]
    # panggilan kedua membaca cache, tanpa jaringan
    baris2 = ambil_data_variabel("KUNCI", "0000", "912", "2024", cache)
    assert len(dipanggil) == 1
    assert baris2 == baris
    assert (cache / "0000_912_2024.json").exists()
