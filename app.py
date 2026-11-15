"""Dashboard statistik spasial kabupaten/kota Indonesia.

Menjalankan: streamlit run app.py
Semua angka bersumber nyata (BPS 2022, SSGI 2022) dan diproses lokal tanpa jaringan.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from spatial_stats_id import spasial
from spatial_stats_id.data import gabung_wilayah, muat_geometri
from spatial_stats_id.weights import bobot_jarak, bobot_queen, ringkas

warnings.filterwarnings("ignore")

st.set_page_config(page_title="spatial-stats-id", layout="wide")

# Palet: teal gelap sebagai warna inti, terracotta hanya di penanda signifikan.
# Warna kuadran mengikuti konvensi peta LISA (Anselin) agar mudah dibaca.
TEAL = "#1F5D62"
TINTA = "#1C2830"
ABU_JELAS = "#5B6B72"

INDIKATOR = {
    "kemiskinan": {
        "kolom": "kemiskinan_p0",
        "label": "Persentase penduduk miskin (P0)",
        "sumber": "BPS 2022",
        "satuan": "%",
    },
    "stunting": {
        "kolom": "stunting",
        "label": "Prevalensi stunting balita",
        "sumber": "SSGI 2022 (Buku Saku Kemenkes)",
        "satuan": "%",
    },
}

KOVARIAT = {
    "ipm": "Indeks Pembangunan Manusia",
    "rls": "Rata-rata lama sekolah 15+ (tahun)",
    "pengeluaran_kapita": "Pengeluaran per kapita disesuaikan (ribu Rp/tahun)",
    "sanitasi_layak": "Rumah tangga akses sanitasi layak (%)",
    "air_layak": "Rumah tangga akses air minum layak (%)",
    "tpt": "Tingkat pengangguran terbuka (%)",
    "pdrb_konstan": "PDRB harga konstan (Rp)",
}


@st.cache_data(show_spinner=False)
def muat_semua():
    return muat_geometri()


@st.cache_data(show_spinner=True)
def analisis(indikator: str, provinsi: str, jenis_bobot: str, ambang: int, alpha: float):
    """Kembalikan bingkai analisis lengkap untuk satu kombinasi kontrol."""
    label = INDIKATOR[indikator]
    gab, _ = gabung_wilayah("kemiskinan")
    kolom = label["kolom"]
    if indikator == "stunting":
        stunting = gabung_wilayah("stunting")[0][["kode", "stunting"]]
        gab = gab.drop(columns=["stunting"], errors="ignore").merge(stunting, on="kode", how="left")
    if provinsi != "Seluruh Indonesia":
        gab = gab[gab["provinsi"] == provinsi]
    ada = gab.dropna(subset=[kolom]).copy()
    if len(ada) == 0:
        return {"kosong": True}
    ids = list(ada["kode"])
    if jenis_bobot == "Queen (batas bersentuhan)":
        _, tetangga, _ = muat_geometri()
        w = bobot_queen(tetangga, ids)
    else:
        latlon = {r["kode"]: (r["lat"], r["lon"]) for _, r in ada.iterrows()}
        w = bobot_jarak(latlon, ids, float(ambang))
    nilai = list(ada[kolom].astype(float))
    hasil = {
        "kosong": False,
        "frame": ada,
        "bobot": ringkas(w),
        "moran": spasial.moran_global(nilai, w),
        "lisa": pd.DataFrame(spasial.lisa(nilai, w, alpha=alpha)),
        "scatter": pd.DataFrame(spasial.moran_scatter(nilai, w)),
        "ids": ids,
        "w": w,
    }
    return hasil


def kalimat_moran(m: dict) -> str:
    p = m["p_sim"]
    if p >= 0.05:
        return ("Moran's I tidak berbeda dari pola acak pada taraf %.2f. "
                "Tidak ada bukti pengelompokan spasial untuk kombinasi pilihan ini." % 0.05)
    kekuatan = "sangat kuat" if m["I"] > 0.6 else ("kuat" if m["I"] > 0.4 else ("sedang" if m["I"] > 0.2 else "lemah"))
    return (
        "Moran's I = %.2f (p = %.3f, %d permutasi): autokorelasi spasial positif %s. "
        "Wilayah bernilai tinggi cenderung bertetangga dengan wilayah bernilai tinggi, "
        "dan berlaku pula untuk wilayah bernilai rendah." % (m["I"], p, m["permutasi"], kekuatan)
    )


def peta_nilai(frame: pd.DataFrame, kolom: str, label: str, geojson: list[dict], judul: str):
    fig = px.choropleth(
        frame,
        geojson={"type": "FeatureCollection", "features": geojson},
        featureidkey="properties.kode",
        locations="kode",
        color=kolom,
        color_continuous_scale="OrRd",
        labels={kolom: label},
        hover_name="nama",
        hover_data={"provinsi": True, kolom: ":.1f", "kode": False},
        fitbounds="locations",
        title=judul,
    )
    fig.update_geos(visible=False, bgcolor="#FAF9F6")
    fig.update_layout(
        height=520,
        margin={"r": 10, "l": 10, "t": 42, "b": 10},
        paper_bgcolor="#FAF9F6",
        font_color=TINTA,
        coloraxis_colorbar={"thickness": 12, "len": 0.75},
    )
    return fig


def peta_klaster(frame: pd.DataFrame, lisa: pd.DataFrame, geojson: list[dict], judul: str):
    gab = frame[["kode", "nama", "provinsi"]].merge(lisa[["kode", "kuadran", "p_sim"]], on="kode")
    urutan = ["High-High", "Low-Low", "High-Low", "Low-High", "Tidak signifikan"]
    fig = px.choropleth(
        gab,
        geojson={"type": "FeatureCollection", "features": geojson},
        featureidkey="properties.kode",
        locations="kode",
        color="kuadran",
        color_discrete_map=spasial.WARNA_KUADRAN,
        category_orders={"kuadran": urutan},
        hover_name="nama",
        hover_data={"provinsi": True, "p_sim": ":.3f", "kuadran": True, "kode": False},
        fitbounds="locations",
        title=judul,
    )
    fig.update_geos(visible=False, bgcolor="#FAF9F6")
    fig.update_layout(
        height=520,
        margin={"r": 10, "l": 10, "t": 42, "b": 10},
        paper_bgcolor="#FAF9F6",
        font_color=TINTA,
        legend_title_text="Klaster LISA",
    )
    return fig


def plot_moran(scatter: pd.DataFrame, lisa: pd.DataFrame, nama_map: dict):
    gab = scatter.merge(lisa[["kode", "kuadran"]], on="kode")
    gab["nama"] = gab["kode"].map(nama_map)
    urutan = ["High-High", "Low-Low", "High-Low", "Low-High", "Tidak signifikan"]
    fig = px.scatter(
        gab,
        x="z",
        y="lag",
        color="kuadran",
        color_discrete_map=spasial.WARNA_KUADRAN,
        category_orders={"kuadran": urutan},
        hover_name="nama",
        hover_data={"z": ":.2f", "lag": ":.2f", "kuadran": False, "kode": False},
        labels={"z": "z (nilai ternormalisasi)", "lag": "Rata-rata tetangga (Wz)"},
    )
    batas = max(gab[["z", "lag"]].abs().max().max() * 1.15, 1.0)
    fig.add_hline(y=0, line_color=ABU_JELAS, line_width=1)
    fig.add_vline(x=0, line_color=ABU_JELAS, line_width=1)
    fig.add_annotation(text="High-High", x=batas * 0.6, y=batas * 0.6, showarrow=False, font_color=ABU_JELAS)
    fig.add_annotation(text="Low-Low", x=-batas * 0.6, y=-batas * 0.6, showarrow=False, font_color=ABU_JELAS)
    fig.add_annotation(text="High-Low", x=batas * 0.6, y=-batas * 0.6, showarrow=False, font_color=ABU_JELAS)
    fig.add_annotation(text="Low-High", x=-batas * 0.6, y=batas * 0.6, showarrow=False, font_color=ABU_JELAS)
    fig.update_layout(height=480, paper_bgcolor="#FAF9F6", font_color=TINTA, legend_title_text="Klaster")
    return fig


# --- tata halaman ---
st.markdown(
    """
    <style>
      .sumber-kecil {color: #5B6B72; font-size: 0.82rem; margin-top: -0.4rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("spatial-stats-id")
st.markdown(
    "Statistik spasial 514 kabupaten/kota: **di mana** indikator mengelompok, "
    "bukan hanya seberapa tinggi. Moran's I global, klaster LISA, dan regresi spasial "
    "dalam satu halaman."
)
st.markdown(
    '<p class="sumber-kecil">Batas wilayah turunan shapefile BIG (mirror GeoJSON publik) · '
    "Kemiskinan: BPS 2022 · Stunting: SSGI 2022, ekstraksi Buku Saku Kemenkes · "
    'Permutasi 999, seed tetap agar hasil dapat direproduksi</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Analisis")
    indikator = st.radio(
        "Indikator",
        ["kemiskinan", "stunting"],
        format_func=lambda k: "%s (%s)" % (INDIKATOR[k]["label"], INDIKATOR[k]["sumber"]),
    )
    _, _, master = muat_semua()
    provinsi = st.selectbox("Cakupan", ["Seluruh Indonesia"] + sorted(master["provinsi"].unique().tolist()))

    st.header("Bobot spasial")
    jenis_bobot = st.radio("Definisi tetangga", ["Queen (batas bersentuhan)", "Jarak centroid"])
    ambang = st.slider("Ambang jarak (km)", 100, 300, 150, step=25, disabled=jenis_bobot != "Jarak centroid")
    alpha = st.selectbox("Taraf signifikansi LISA", [0.01, 0.05, 0.10], index=1)

hasil = analisis(indikator, provinsi, jenis_bobot, ambang, alpha)

if hasil.get("kosong"):
    st.info(
        "Tidak ada nilai %s untuk cakupan ini. SSGI 2022 tidak menerbitkan angka kab/kota "
        "untuk provinsi Nusa Tenggara Timur; pilih indikator kemiskinan atau cakupan lain."
        % INDIKATOR[indikator]["label"]
    )
    st.stop()

label = INDIKATOR[indikator]
frame = hasil["frame"]
kolom = label["kolom"]
geojson, _, _ = muat_semua()
nama_map = dict(zip(frame["kode"], frame["nama"]))

moran = hasil["moran"]
bobot = hasil["bobot"]
lisa = hasil["lisa"]

# satu kotak konteks per halaman: angka kunci plus maknanya
st.markdown(
    """
    <div style="border-left:4px solid #1F5D62; padding:0.4rem 1rem; margin:0.6rem 0 0.2rem 0;">
      <div style="font-size:1.05rem; color:#1C2830;">
        <b>Moran's I = %.2f</b> (p = %.3f, n = %d) pada %s, cakupan %s.
      </div>
      <div style="color:#5B6B72;">%s</div>
    </div>
    """
    % (
        moran["I"],
        moran["p_sim"],
        moran["n"],
        label["label"].lower(),
        provinsi.lower() if provinsi != "Seluruh Indonesia" else "seluruh Indonesia",
        kalimat_moran(moran),
    ),
    unsafe_allow_html=True,
)
if bobot["n_isolates"]:
    st.caption(
        "%d wilayah tanpa tetangga pada bobot ini (pulau) ikut dalam ringkasan global "
        "namun tak terlibat asosiasi lokal; definisi tetangga: %s."
        % (bobot["n_isolates"], jenis_bobot.split(" (")[0])
    )

tab_peta, tab_moran, tab_reg, tab_metode = st.tabs(["Peta & klaster", "Moran's I", "Regresi spasial", "Metode & sumber"])

with tab_peta:
    kiri, kanan = st.columns(2, gap="medium")
    with kiri:
        st.plotly_chart(
            peta_nilai(frame, kolom, label["label"], geojson, "%s (%s)" % (label["label"], label["sumber"])),
            width="stretch",
        )
    with kanan:
        st.plotly_chart(
            peta_klaster(frame, lisa, geojson, "Klaster LISA, taraf %.2f" % alpha),
            width="stretch",
        )
    st.caption(
        "High-High: nilai tinggi dikelilingi tetangga bernilai tinggi (kandidat intervensi terpadu). "
        "Low-Low: nilai rendah mengelompok (kandidat percontohan/praktik baik). "
        "High-Low dan Low-High: pencilan spasial."
    )
    hitung = lisa["kuadran"].value_counts().reindex(
        ["High-High", "Low-Low", "High-Low", "Low-High", "Tidak signifikan"]
    ).fillna(0).astype(int)
    st.write(hitung.rename_axis("Kuadran").rename("Jumlah wilayah").to_frame())
    pilihan = st.selectbox("Daftar wilayah per klaster", [k for k in hitung.index if hitung[k] > 0])
    daftar = lisa[lisa["kuadran"] == pilihan].merge(
        frame[["kode", "nama", "provinsi"]], on="kode"
    )[["nama", "provinsi", "z", "p_sim"]].sort_values("z", ascending=(pilihan in ("Low-Low", "Low-High")))
    st.dataframe(daftar, width="stretch", hide_index=True)
    st.download_button(
        "Unduh klasifikasi LISA (CSV)",
        data=lisa.merge(frame[["kode", "nama", "provinsi"]], on="kode").to_csv(index=False).encode("utf-8"),
        file_name="lisa_%s_%s.csv" % (indikator, provinsi.replace(" ", "_").lower()),
        mime="text/csv",
    )

with tab_moran:
    st.plotly_chart(plot_moran(hasil["scatter"], lisa, nama_map), width="stretch")
    st.caption(
        "Setiap titik satu wilayah: sumbu mendatar nilai ternormalisasi wilayah, sumbu tegak "
        "rata-rata tetangganya. Titik di kuadran kanan-atas berkontribusi pada autokorelasi positif. "
        "Kemiringan garis (tidak digambar) setara Moran's I = %.2f." % moran["I"]
    )

with tab_reg:
    st.markdown(
        "Model membandingkan regresi biasa (OLS) dengan dua model spasial: "
        "**Lag** (nilai wilayah dipengaruhi tetangganya) dan **Error** (sisa model berpola spasial). "
        "Kovariat bersumber tabel BPS 2022."
    )
    x_pilihan = st.multiselect(
        "Kovariat", list(KOVARIAT), default=["ipm"], format_func=lambda k: KOVARIAT[k]
    )
    if not x_pilihan:
        st.info("Pilih minimal satu kovariat untuk menjalankan model.")
        st.stop()
    data_reg = frame.dropna(subset=[kolom] + x_pilihan)
    if len(data_reg) < 30:
        st.error("Sampel terlalu kecil (%d wilayah) untuk estimasi yang berarti." % len(data_reg))
        st.stop()
    w = hasil["w"]
    ids_reg = list(data_reg["kode"])
    if set(ids_reg) == set(hasil["ids"]):
        w_reg = w
    else:
        from spatial_stats_id.weights import subset_tetangga

        _, tetangga, _ = muat_semua()
        w_reg = bobot_queen(subset_tetangga(tetangga, ids_reg), ids_reg)
    reg = spasial.regresi_spasial(
        list(data_reg[kolom].astype(float)),
        data_reg[x_pilihan].astype(float).values.tolist(),
        w_reg,
        kolom,
        x_pilihan,
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("OLS R²", "%.2f" % reg["ols"]["r2"])
    k2.metric("ρ (lag)", "%.2f%s" % (reg["lag"]["rho"], "" if reg["lag"]["rho_p"] is None else " (p=%.3f)" % reg["lag"]["rho_p"]))
    k3.metric("λ (error)", "%.2f%s" % (reg["error"]["lambda"], "" if reg["error"]["lr_p"] is None else " (p=%.3f)" % reg["error"]["lr_p"]))
    st.markdown("**Uji rasio likelihood terhadap OLS** (df = 1)")
    st.write(
        "Lag: LR = %.1f, p = %.2e. Error: LR = %.1f, p = %.2e."
        % (reg["lag"]["lr_stat"], reg["lag"]["lr_p"], reg["error"]["lr_stat"], reg["error"]["lr_p"])
    )
    if reg["lag"]["lr_p"] < 0.05 or reg["error"]["lr_p"] < 0.05:
        st.markdown(
            "Dependensi spasial signifikan: koefisien OLS bisa bias atau tidak efisien; "
            "gunakan model lag/error untuk interpretasi."
        )
    else:
        st.markdown("Dependensi spasial tidak signifikan pada model ini; OLS cukup digunakan.")
    st.markdown("**Koefisien OLS**")
    st.dataframe(pd.DataFrame(reg["ols"]["koef"]), width="stretch", hide_index=True)
    st.markdown("**Koefisien ML_Lag**")
    st.dataframe(pd.DataFrame(reg["lag"]["koef"]), width="stretch", hide_index=True)
    if reg["ols"]["bp_p"] is not None and reg["ols"]["bp_p"] < 0.05:
        st.caption("Catatan: uji Breusch-Pagan menolak homoskedastisitas (p = %.3f); "
                   "nilai p koefisien tetap informatif namun interpretasi r² perlu hati-hati." % reg["ols"]["bp_p"])

with tab_metode:
    st.markdown("**Mengapa klaster spasial penting untuk kebijakan?**")
    st.markdown(
        "Angka rata-rata provinsi bisa menyembunyikan konsentrasi: dua provinsi dengan rata-rata sama "
        "bisa punya pola sangat berbeda. Klaster High-High menunjukkan daerah yang saling bersentuhan "
        "sama-sama buruk, sehingga intervensi perbatasan atau lintas kabupaten jauh lebih efisien "
        "daripada program per wilayah sendiri-sendiri. Klaster Low-Low menandai praktik baik yang "
        "bisa dijadikan rujukan. Pencilan (High-Low, Low-High) layak diperiksa satu per satu."
    )
    st.markdown("**Ringkasan metode**")
    st.markdown(
        "1. **Moran's I global** mengukur korelasi antara nilai wilayah dan rata-rata tetangganya "
        "terhadap pola acak (permutasi 999 kali). Nilai mendekati +1 berarti pengelompokan kuat.\n"
        "2. **LISA (Local Indicators of Spatial Association, Anselin 1995)** menandai wilayah yang "
        "menyumbang autokorelasi secara signifikan, diklasifikasikan empat kuadran.\n"
        "3. **Regresi spasial**: ML_Lag memasukkan nilai tetangga sebagai pengaruh langsung (ρ), "
        "ML_Error menangkap pola spasial pada sisa model (λ). Keduanya dibandingkan dengan OLS "
        "melalui uji rasio likelihood.\n"
        "4. Bobot Queen dihitung dari batas wilayah yang bersentuhan (geometri resolusi penuh); "
        "bobot jarak memakai centroid dengan jarak haversine."
    )
    st.markdown("**Sumber data dan catatan kejujuran**")
    st.markdown(
        "- Geometri: turunan shapefile batas administrasi BIG, melalui mirror GeoJSON publik "
        "(514 kab/kota); sederhana untuk tampilan, tetangga dihitung dari geometri penuh.\n"
        "- Kemiskinan dan kovariat: BPS 2022 (P0, IPM, RLS, pengeluaran per kapita, sanitasi, air, "
        "TPT, PDRB konstan).\n"
        "- Stunting: SSGI 2022 dari Buku Saku Hasil SSGI 2022 (Badan Kebijakan Pembangunan Kesehatan, "
        "Kemenkes), diekstraksi dari grafik halaman provinsi dan divalidasi silang dengan publikasi "
        "resmi (contoh: Asmat 54,5%, Kota Batu 4,8%).\n"
        "- SSGI 2022 tidak menerbitkan angka kab/kota untuk 22 wilayah NTT sehingga tampil sebagai "
        "data tidak tersedia.\n"
        "- Tabel BPS 2022 memakai nama lama 'Pontianak' untuk Kabupaten Mempawah; keduanya digabung.\n"
        "- Nilai ekstraksi bersifat pembacaan grafik resmi (presisi 0,1 poin). Untuk penggunaan formal, "
        "cocokkan ke tabel SSGI dalam Angka.\n"
        "- Dashboard bersifat edukatif dan bukan dokumen resmi untuk penetapan kebijakan."
    )
    st.markdown("**Referensi**")
    st.markdown(
        "Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. *Biometrika*, 37(1/2), 17-23.  \n"
        "Anselin, L. (1995). Local indicators of spatial association: LISA. *Geographical Analysis*, 27(2), 93-115."
    )

st.caption(
    "Repositori: pipeline data, paket analisis, dan pengujian di GitHub. "
    "Jalankan ulang pipeline untuk memperbarui data melalui WebAPI BPS (lihat scripts/)."
)
