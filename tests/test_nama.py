"""Pengujian normalisasi nama wilayah."""
from spatial_stats_id.nama import TYPO_STEM, cocok_stem, normal_provinsi, pisah_tipe


def pisah(kasus, harapan):
    assert pisah_tipe(kasus) == harapan, f"{kasus!r} -> {pisah_tipe(kasus)}, harapan {harapan}"


def test_pisah_tipe_varian_awalan():
    pisah("Kabupaten Aceh Barat", ("kabupaten", "ACEH BARAT"))
    pisah("Kab. Aceh Utara", ("kabupaten", "ACEH UTARA"))
    pisah("Kota Jakarta Pusat", ("kota", "JAKARTA PUSAT"))
    pisah("Simeulue", ("kabupaten", "SIMEULUE"))
    pisah("Kabupaten Kota Baru", ("kabupaten", "KOTA BARU"))


def test_normal_provinsi_alias():
    assert normal_provinsi("NTB") == "NUSA TENGGARA BARAT"
    assert normal_provinsi("D I YOGYAKARTA") == "DAERAH ISTIMEWA YOGYAKARTA"
    assert normal_provinsi("KEP. BANGKA BELITUNG") == "KEPULAUAN BANGKA BELITUNG"
    assert normal_provinsi("KEP.BANGKA BELITUNG") == "KEPULAUAN BANGKA BELITUNG"
    assert normal_provinsi("aceh ") == "ACEH"


def test_cocok_stem_persis_dan_awalan():
    kandidat = ["BENGKULU UTARA", "BENGKULU SELATAN", "KOTA BENGKULU"]
    assert cocok_stem("BENGKULU UTARA", kandidat) == ("BENGKULU UTARA", "persis")
    stem, alasan = cocok_stem("BENGKULU SELA", kandidat)
    assert stem == "BENGKULU SELATAN"
    assert cocok_stem("BOGUE", kandidat)[0] is None


def test_cocok_stem_menang_skor_atas_awalan():
    # 'TULANG BAWANG' lebih mirip 'TULANGBAWANG' (0,96) daripada sekadar
    # berawalan sama dengan 'TULANG BAWANG BARAT' (0,81).
    kandidat = ["TULANGBAWANG", "TULANG BAWANG BARAT"]
    assert cocok_stem("TULANG BAWANG", kandidat) == ("TULANGBAWANG", "mirip")


def test_cocok_stem_ambigu():
    kandidat = ["HALMAHERA TENGAH", "HALMAHERA TENGGARA"]
    stem, alasan = cocok_stem("HALMAHERA TE", kandidat)
    assert stem is None and alasan == "ambigu"
    assert cocok_stem("PONTIANAKX", kandidat) == (None, "tidak_ada")


def test_typo_stem_kotabaru():
    assert TYPO_STEM["KOTA BARU"] == "KOTABARU"
