# Sumber data mentah (tidak dikomit, diambil ulang lewat scripts/fetch_sources.py)

| Berkas | Sumber | Ketentuan |
| --- | --- | --- |
| all_kabkota_ind.geojson | github.com/eppofahmi/geojson-indonesia (turunan shapefile batas administrasi BIG) | data geospasial BIG |
| buku_saku_ssgi_2022.pdf | Buku Saku Hasil SSGI 2022, repository.badankebijakan.kemkes.go.id (eprint 4855) | publikasi resmi Kemenkes |
| indikator_bps_2022.csv | Kaggle dlausl/klasifikasi-tingkat-kemiskinan-di-indonesia, tabel indikator BPS 2022 | Apache 2.0 |

Pipeline merujuk berkas di folder ini sebagai masukan; `scripts/fetch_sources.py` mengunduh
semuanya sehingga folder bisa kosong saat repo dikloning.
