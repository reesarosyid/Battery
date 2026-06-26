# Reproduksi Data Mining Elektroda Baterai (Moses et al. 2022)

Re-implementasi pipeline data mining dari:

> I. A. Moses, V. Barone, J. E. Peralta, *Accelerating the discovery of
> battery electrode materials through data mining and deep learning models*,
> Journal of Power Sources 546 (2022) 231977.

Pipeline ini menambang pasangan elektroda charged/discharged dari Materials
Project (MP) dan AFLOW, menghitung properti (V_av, ΔV%, kapasitas, energi
spesifik), lalu membuat fitur berbasis komposisi untuk model deep learning.

---

## ⚠️ Catatan penting soal "data identik dengan paper"

Mereproduksi data **persis sama** dengan paper sudah TIDAK mungkin, karena:

1. **API lama (legacy MAPI) pensiun 30 September 2025.** Paper memakai API
   itu; pipeline ini memakai client resmi terbaru `mp-api`.
2. **Database MP terus diperbarui** (kini versi v2025.09.25). Snapshot 2022
   milik paper berisi 144,595 senyawa; jumlah, energi DFT+U, dan struktur
   sekarang berbeda. Maka pasangan dan nilai V_av/ΔV% pasti bergeser tipis.

Tiga opsi tergantung tujuan:

| Tujuan | Opsi | Cara |
|---|---|---|
| Butuh **datanya** | A | Unduh database 191,625 instance langsung dari Supplementary Information paper (https://doi.org/10.1016/j.jpowsour.2022.231977) |
| Mau **mendekati** snapshot 2022 | B | Pakai bulk download legacy MP "snapshot 28 Oktober 2022" dari MP AWS, lalu jalankan modul `pair_matching` + `properties` di atasnya |
| Mau **mereproduksi metodologi** | C | Jalankan pipeline ini di atas data MP/AFLOW terkini (default) |

Pipeline ini adalah **Opsi C**. Hasilnya *setara secara metodologis*, bukan
identik byte-per-byte.

---

## Instalasi

```bash
pip install -r requirements.txt
```

Dapatkan API key MP gratis di https://next-gen.materialsproject.org/api lalu:

```bash
export MP_API_KEY="kunci_anda"
```

## Pemakaian

```bash
# 1. Unduh material mentah + energi referensi logam murni
python run_pipeline.py fetch                 # MP saja
python run_pipeline.py fetch --with-aflow    # + AFLOW (berat)

# 2. Cari pasangan elektroda & hitung properti
python run_pipeline.py pairs --source mp     # -> data/mp_pairs.csv

# 3. Featurize untuk ML (matminer + PCA)
python run_pipeline.py featurize --source mp # -> data/features.csv

# atau sekaligus:
python run_pipeline.py all
```

Verifikasi logika inti tanpa API:

```bash
python test_logic.py
```

---

## Struktur & pemetaan ke paper

| File | Tahap paper | Isi |
|---|---|---|
| `config.py` | — | Konstanta: 10 ion aktif, valensi, Faraday, filter |
| `fetch_mp.py` | Bagian 2.1 | Unduh & bersihkan material MP (API baru); energi E_M |
| `fetch_aflow.py` | Bagian 2.1 | Unduh material AFLOW via AFLUX |
| `pair_matching.py` | Fig. 1, Bagian 2.1 | **Algoritma inti** cari pasangan charged/discharged |
| `properties.py` | Eq. (1)–(4) | Hitung V_av, ΔV%, kapasitas C, energi spesifik SE |
| `featurize.py` | Tabel 1, Bagian 2.2 | Fitur matminer + normalisasi + PCA 120 komponen |
| `run_pipeline.py` | — | Orkestrator end-to-end |
| `test_logic.py` | — | Uji unit (lulus: pasangan, scaling, voltase) |

### Detail algoritma inti (`pair_matching.py`)

Mengikuti Fig. 1 paper, untuk tiap pasangan (N, N*):

1. Spesies atom sama, atau hanya berbeda pada logam aktif M.
2. Rasio jumlah tiap spesies non-M konsisten (commensurate); hanya M beda.
3. Skala sel lebih kecil dengan faktor `f = nA/nA*`; energi & volume ikut.
4. Jumlah M lebih banyak = discharged; sisanya = charged.

**Optimasi:** alih-alih membandingkan O(n²) seluruh material (>100k, tidak
praktis), material dikelompokkan per "fingerprint kerangka" (formula non-M
ternormalisasi), lalu pasangan hanya dicari dalam grup yang sama. Hasil
setara dengan brute-force tetapi jauh lebih cepat.

---

## Hal yang mungkin perlu disesuaikan agar lebih dekat ke paper

- **Konvensi energi.** Paper memakai "energi DFT+U unit cell". Pipeline ini
  memakai `uncorrected_energy_per_atom × nsites` agar konsisten dengan energi
  logam referensi. Jika ingin koreksi MP/anion correction, sesuaikan di
  `fetch_mp.py`.
- **Jumlah fitur matminer.** Paper menyebut 151 fitur/formula. Set featurizer
  standar (Ward et al.) menghasilkan angka yang sedikit berbeda tergantung
  versi matminer. Sesuaikan daftar di `featurize._build_featurizer()` bila
  ingin mencocokkan persis.
- **Filter ML.** Pembuangan instance ekstrem (|V_av|>13, ΔV%>500) ada di
  `config.py` dan diterapkan pada tahap training model (bukan database mentah).
