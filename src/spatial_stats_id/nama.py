"""Normalisasi nama wilayah dan pencocokan label sumber data ke kode BPS.

Sumber data memakai gaya nama berbeda: geometri BIG memakai alt_name
'KABUPATEN SIMEULUE', tabel BPS menulis 'Simeulue' atau 'Kota Jakarta Pusat',
Buku Saku SSGI memotong label grafik ('Kab. Bengkulu Sela'). Semua diarahkan
ke satu pasangan (tipe, stem) per provinsi.
"""
from __future__ import annotations

import re
from difflib import get_close_matches, SequenceMatcher

ALIAS_PROVINSI = {
    "NTB": "NUSA TENGGARA BARAT",
    "NTT": "NUSA TENGGARA TIMUR",
    "KEP. BANGKA BELITUNG": "KEPULAUAN BANGKA BELITUNG",
    "KEP.BANGKA BELITUNG": "KEPULAUAN BANGKA BELITUNG",
    "KEP. RIAU": "KEPULAUAN RIAU",
    "DI YOGYAKARTA": "DAERAH ISTIMEWA YOGYAKARTA",
    "D I YOGYAKARTA": "DAERAH ISTIMEWA YOGYAKARTA",
    "DKI JAKARTA": "DKI JAKARTA",
    "BANGKA BELITUNG": "KEPULAUAN BANGKA BELITUNG",
}

_AWALAN = ("KABUPATEN ", "KOTA ", "KAB. ", "KOT. ")
_SPASI = re.compile(r"\s+")

# Koreksi ejaan: BPS menulis 'Kotabaru' satu kata, mirror geometri memisahkannya.
TYPO_STEM = {"KOTA BARU": "KOTABARU"}


def rapikan_spasi(s: str) -> str:
    return _SPASI.sub(" ", s.strip())


def normal_provinsi(nama: str) -> str:
    """Ke bentuk baku huruf besar, dengan alias umum dilewaskan."""
    s = rapikan_spasi(nama).upper()
    return ALIAS_PROVINSI.get(s, s)


def pisah_tipe(nama: str) -> tuple[str, str]:
    """Pisahkan 'Kabupaten/Kota/Kab. X' menjadi (tipe, stem).

    Nama tanpa awalan dianggap kabupaten (konvensi tabel BPS).
    """
    s = rapikan_spasi(nama)
    for awalan in _AWALAN:
        if s.upper().startswith(awalan):
            tipe = "kota" if awalan.startswith("KOT") else "kabupaten"
            return tipe, rapikan_spasi(s[len(awalan):]).upper()
    return "kabupaten", s.upper()


def cocok_stem(label: str, kandidat: list[str]) -> tuple[str | None, str]:
    """Cocokkan stem label ke daftar stem kandidat.

    Urutan percobaan: persis, awalan (label buku terpotong), kemiripan. Saat
    keduanya menunjuk kandidat berbeda, skor kemiripan tertinggi yang menang:
    'Tulang Bawang' harus jatuh ke 'TULANGBAWANG' (0,96), bukan ke
    'TULANG BAWANG BARAT' yang sekadar berawalan sama.
    """
    if label in kandidat:
        return label, "persis"
    berawalan = [k for k in kandidat if k.startswith(label)]
    mirip = get_close_matches(label, kandidat, n=1, cutoff=0.85)
    if len(berawalan) > 1:
        # label terpotong menyentuh beberapa wilayah sekaligus: tak ada cara
        # membedakannya dari teks yang ada
        return None, "ambigu"
    if berawalan and mirip and mirip[0] not in berawalan:
        skor_mirip = SequenceMatcher(None, label, mirip[0]).ratio()
        skor_awalan = max(SequenceMatcher(None, label, b).ratio() for b in berawalan)
        if skor_mirip >= skor_awalan:
            return mirip[0], "mirip"
    if len(berawalan) == 1:
        return berawalan[0], "awalan"
    if mirip:
        return mirip[0], "mirip"
    if berawalan or mirip:
        return None, "ambigu"
    return None, "tidak_ada"


def skor_mirip(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()
