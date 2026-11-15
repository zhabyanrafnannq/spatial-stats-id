"""Pengujian artefak data yang dikomit (butuh data/processed tersedia)."""
import pandas as pd
import pytest

from spatial_stats_id.data import gabung_wilayah, muat_geometri


@pytest.fixture(scope="module")
def geometri():
    return muat_geometri()


def test_master_514_tanpa_duplikat(geometri):
    _, tetangga, master = geometri
    assert len(master) == 514
    assert master["kode"].nunique() == 514


def test_tetangga_simetris_dan_seluruh_id_ada(geometri):
    _, tetangga, master = geometri
    id_master = set(master["kode"])
    assert set(tetangga) == id_master
    for k, daftar in tetangga.items():
        for t in daftar:
            assert k in tetangga[t], f"tetangga tak simetris {k}-{t}"


def test_gabung_kemiskinan_penuh():
    gab, kolom = gabung_wilayah("kemiskinan")
    assert len(gab) == 514
    assert "kemiskinan_p0" in kolom
    assert gab["kemiskinan_p0"].notna().sum() == 514
    assert (gab["kemiskinan_p0"].astype(float).between(0, 100)).all()


def test_gabung_stunting_ntt_kosong():
    gab, kolom = gabung_wilayah("stunting")
    assert "stunting" in kolom
    berdata = gab.dropna(subset=["stunting"])
    assert len(berdata) == 492
    ntt = berdata[berdata["provinsi"] == "NUSA TENGGARA TIMUR"]
    assert len(ntt) == 0
    assert (berdata["stunting"].astype(float).between(0, 100)).all()


def test_kode_tipe_konsisten(geometri):
    _, _, master = geometri
    kota = master[master["tipe"] == "kota"]
    # kode kota berpola 71-79 di dua digit terakhir
    assert (kota["kode"].str[-2] == "7").all()
    assert "Kota Jakarta Pusat" in set(kota["nama"])
