# 🔍 SKEMA SCRAPING DATA - VISUAL EXPLANATION

## STEP 1: Pahami Tujuan Akhir

Kita ingin membuat model ML yang bisa **predict voltase & volume change** dari suatu material.

```
INPUT: Material properties (chemical formula, structure, dll)
   ↓
MODEL: Neural Network dengan 120 features
   ↓
OUTPUT: Prediksi V_av (voltage) & dV% (volume change)
```

Tapi model tidak bisa langsung makan "LiCoO2" sebagai input. Harus convert ke **120 angka**.

---

## STEP 2: Dari Mana Data Berasal?

Kita punya 2 database besar:
- **Materials Project (MP)**: 144,595 materials
- **AFLOW**: 729,840 materials

Tapi tidak semua bisa jadi baterai. Hanya yang punya "pasangan" (charged state & discharged state).

### Contoh Pasangan:
```
Discharged state: LiCoO2 (Li banyak, energi rendah, volume besar)
      ↕ 
      (remove 1 Li ion)
      ↕
Charged state:   CoO2   (Li sedikit, energi tinggi, volume kecil)
```

**Pasangan ini PENTING** karena dari selisih energi & volume, kita bisa hitung:
- V_av (average voltage)
- dV% (volume change)
- Capacity (charge capacity)
- Specific Energy (energy density)

---

## STEP 3: Skema Database

```
┌─────────────────────────────────────────────────────────────────┐
│ MATERIALS PROJECT / AFLOW DATABASE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ material_id: mp-3346412                                         │
│ formula_pretty: "Na2CaMg(SO4)3"                                 │
│ composition: {Na: 12, Ca: 6, Mg: 6, S: 18, O: 72}              │
│ structure: [3D atomic coordinates]                              │
│ volume: 1496.31 Å³                                              │
│ energy_per_atom: -8.14 eV/atom                                  │
│ symmetry.number: 1 (triclinic)                                  │
│ symmetry.crystal_system: "Triclinic"                            │
│ band_gap: 2.45 eV                                               │
│ nsites: 114 atoms per unit cell                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## STEP 4: Proses Scraping (TAHAP 1 - Sudah Anda Lakukan)

```
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 1: FETCH DATA & FIND PAIRS                                │
└─────────────────────────────────────────────────────────────────┘

1. Download dari MP API:
   ├─ 3,818 materials dari MP
   ├─ 229,741 materials dari AFLOW
   └─ Total: 233,559 materials

2. Filter untuk solid structures saja
   (hilangkan non-solid, duplicates)

3. Cari pasangan untuk setiap metal (Li, Na, K, Mg, Ca, Al, Zn, Y, Rb, Cs):
   
   Untuk SETIAP metal:
   ├─ Cari material A & B yang:
   │  ├─ Punya elemen yang SAMA (kecuali metal)
   │  ├─ Metal count BERBEDA (A lebih banyak = discharged)
   │  └─ Framework commensurate (bisa di-scale)
   │
   └─ Contoh untuk Li:
      ├─ Material A: LiCoO2 (1 Li, 1 Co, 2 O)
      ├─ Material B: CoO2  (0 Li, 1 Co, 2 O)
      └─ MATCH! → Pasangan valid

4. Compute properties untuk tiap pasangan:
   ├─ V_av = (E_discharged - E_charged - Δx*E_metal) / (q*Δx)
   ├─ dV% = |V_discharged - V_charged| / min(V) * 100
   ├─ Capacity = (n * Faraday * 1000) / (3600 * molar_mass)
   └─ SE = Capacity * V_av

HASIL: Dataset_BOTH.csv (1.77M pairs, 16 columns)
       ├─ metal, valence
       ├─ discharged_id, discharged_formula
       ├─ charged_id, charged_formula
       ├─ discharged_sg, charged_sg
       ├─ discharged_cs, charged_cs
       ├─ x1_charged, x2_discharged
       └─ V_av, dV_percent, capacity_mAh_g, specific_energy_Wh_kg
```

**Status Anda: ✅ SELESAI**

---

## STEP 5: Ekstraksi Fitur (TAHAP 2 - YANG BELUM ANDA LAKUKAN)

Sekarang kita punya 1.77M pasangan. Tapi **chemical formula adalah STRING**, 
model ML tidak bisa langsung pakai string. **Harus convert ke NUMBERS**.

### Contoh Konversi:

```
INPUT FORMULA:
┌──────────────┐
│ "LiCoO2"     │
└──────────────┘
        ↓
  Gunakan MATMINER
        ↓
OUTPUT FEATURES (151 angka):
┌────────────────────────────────────────────────────┐
│ num_elements: 3                                    │
│ stoich_p2: 0.375                                   │
│ stoich_p5: 0.254                                   │
│ ...                                                │
│ X_mean: 2.45 (electronegativity rata-rata)         │
│ X_min: 0.98 (Li paling negatif)                    │
│ X_max: 3.44 (O paling positif)                     │
│ X_std: 1.23                                        │
│ ...                                                │
│ atomic_radius_mean: 95.3                           │
│ atomic_radius_std: 47.5                            │
│ ...                                                │
│ valence_mean: 5.33                                 │
│ Z_mean: 12.3 (atomic number rata-rata)            │
│ group_mean: 10 (periodic table group rata-rata)   │
│ ...                                                │
│ [dan ~100 fitur lainnya]                          │
└────────────────────────────────────────────────────┘
       (TOTAL: 151 numbers per formula)
```

### Mengapa Perlu Konversi?

```
MATMINER extract informasi chemistry dari formula:

"LiCoO2" → Matminer baca → Extract elemen (Li, Co, O)
         → Hitung jumlah atom tiap elemen
         → Ambil properti fisik tiap elemen dari DB
         → Aggregate (mean, std, min, max, range)
         → Output 151 numbers

Contoh properti per elemen:
  Li: X=0.98, atomic_radius=152pm, Z=3, mass=6.94, group=1, valence=1
  Co: X=1.88, atomic_radius=135pm, Z=27, mass=58.93, group=9, valence=9
  O:  X=3.44, atomic_radius=60pm,  Z=8,  mass=16.00, group=16, valence=6

Aggregate (rata-rata untuk LiCoO2):
  X_mean = (0.98 + 1.88 + 3.44 + 3.44) / 4 = 2.44
  atomic_radius_mean = (152 + 135 + 60 + 60) / 4 = 101.75
  Z_mean = (3 + 27 + 8 + 8) / 4 = 11.5
  ...
```

### Tahap 2 - Pipeline:

```
Dataset_BOTH.csv
   ↓
┌──────────────────────────────────────────┐
│ TAHAP 2: FEATURE EXTRACTION              │
├──────────────────────────────────────────┤
│                                          │
│ For each row (1.77M rows):               │
│  1. Ambil discharged_formula             │
│     → "LiCoO2"                           │
│     → Pass ke Matminer                   │
│     → Get 151 features                   │
│     → Column: disch__X_mean, etc         │
│                                          │
│  2. Ambil charged_formula                │
│     → "CoO2"                             │
│     → Pass ke Matminer                   │
│     → Get 151 features                   │
│     → Column: chg__X_mean, etc           │
│                                          │
│  3. Combine:                             │
│     → 10 primary features (sudah ada)    │
│     → 151 discharged features (baru)     │
│     → 151 charged features (baru)        │
│     → Total: 312 features                │
│     → Remove 4 zero-value columns        │
│     → Result: 308 features               │
│                                          │
└──────────────────────────────────────────┘
   ↓
Final_Features.csv (1.77M × 308 columns)
   ↓
┌──────────────────────────────────────────┐
│ TAHAP 3: PREPROCESSING                   │
├──────────────────────────────────────────┤
│ 1. Normalisasi (StandardScaler)          │
│    → Mean = 0, Std = 1                   │
│ 2. PCA dimensionality reduction          │
│    → 308 → 120 components                │
│    → 99.8% variance retained             │
│ 3. Filter outliers                       │
│    → V_av: -13 to 13V                    │
│    → dV%: < 500%                         │
│    → Remove ~5% data                     │
│                                          │
└──────────────────────────────────────────┘
   ↓
ML_Ready_Dataset.csv (1.68M × 124 cols)
   → 120 PCA components (features)
   → 4 targets (V_av, dV%, capacity, SE)
   ↓
┌──────────────────────────────────────────┐
│ TAHAP 4: MODEL TRAINING                  │
├──────────────────────────────────────────┤
│ Split: 90% train, 10% test               │
│ Model: Deep Neural Network (7 layers)    │
│ Input: 120 features                      │
│ Output: Predict V_av & dV%               │
│ Loss: Mean Absolute Error (MAE)          │
│                                          │
└──────────────────────────────────────────┘
```

---

## STEP 6: Visualisasi Komplet

```
                    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                    ┃ Materials Project / AFLOW DB      ┃
                    ┃ 233,559 materials                 ┃
                    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                   ↓
        ┌──────────────────────────────────────────────────┐
        │ TAHAP 1: Fetch & Find Pairs (✅ SUDAH JALAN)     │
        │ Output: Dataset_BOTH.csv (1.77M × 16 cols)      │
        └──────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ Dataset_BOTH.csv (1.77M rows)                                   │
├─────────────────────────────────────────────────────────────────┤
│ metal │ valence │ discharged_id │ discharged_formula │ ... │    │
│────────────────────────────────────────────────────────────────  │
│ Li    │ 1       │ mp-123456     │ LiCoO2             │ ... │    │
│ Li    │ 1       │ mp-123456     │ LiCoO2             │ ... │    │
│ Na    │ 1       │ mp-234567     │ NaFe2O2            │ ... │    │
│ ...   │ ...     │ ...           │ ...                │ ... │    │
└─────────────────────────────────────────────────────────────────┘
                                   ↓
        ┌──────────────────────────────────────────────────┐
        │ TAHAP 2: Extract Features (❌ BELUM)             │
        │ Use: Matminer library                            │
        │ Input: Formula strings                           │
        │ Output: 151 features per formula                 │
        └──────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ Final_Dataset.csv (1.77M rows × 308 cols)                       │
├─────────────────────────────────────────────────────────────────┤
│ metal │ valence │ ... │ disch__X_mean │ disch__stoich_p2 │...│  │
│────────────────────────────────────────────────────────────────  │
│ Li    │ 1       │ ... │ 2.45          │ 0.375            │...│  │
│ ...   │ ...     │ ... │ ...           │ ...              │...│  │
└─────────────────────────────────────────────────────────────────┘
                                   ↓
        ┌──────────────────────────────────────────────────┐
        │ TAHAP 3: Normalize & PCA (❌ BELUM)              │
        │ StandardScaler → PCA(120 components)             │
        │ Output: 120 PCA features                         │
        └──────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ ML_Ready.csv (1.68M rows × 124 cols)                            │
├─────────────────────────────────────────────────────────────────┤
│ PC1    │ PC2    │ ... │ PC120  │ V_av  │ dV%   │ capacity │ SE  │
│──────────────────────────────────────────────────────────────────│
│ -0.45  │ 0.32   │ ... │ 0.18   │ 3.14  │ 15.2  │ 198.6    │625  │
│ ...    │ ...    │ ... │ ...    │ ...   │ ...   │ ...      │ ..  │
└─────────────────────────────────────────────────────────────────┘
                                   ↓
        ┌──────────────────────────────────────────────────┐
        │ TAHAP 4: Train DNN Model (❌ BELUM)              │
        │ Input: 120 PCA components                        │
        │ Output: Predict V_av & dV%                       │
        └──────────────────────────────────────────────────┘
```

---

## STEP 7: Contoh DATA FLOW untuk 1 Material

```
┌─────────────────────────────────────────────────────────────┐
│ CONTOH: 1 Pasangan Electrode Pair                           │
└─────────────────────────────────────────────────────────────┘

STEP 1: GET DARI API
────────────────────
Discharge electrode: mp-123456
  ├─ formula_pretty: "LiCoO2"
  ├─ composition: {Li: 1, Co: 1, O: 2}
  ├─ volume: 195.5 Å³
  ├─ energy_per_atom: -4.2 eV/atom
  ├─ symmetry.number: 227 (Fm-3m - cubic)
  └─ symmetry.crystal_system: "Cubic"

Charge electrode: mp-234567
  ├─ formula_pretty: "CoO2"
  ├─ composition: {Co: 1, O: 2}
  ├─ volume: 150.3 Å³
  ├─ energy_per_atom: -3.8 eV/atom
  ├─ symmetry.number: 166
  └─ symmetry.crystal_system: "Trigonal"

STEP 2: COMPUTE PRIMARY PROPERTIES
────────────────────────────────────
Metal: Li
Valence: 1
n_metal_charged: 0
n_metal_discharged: 1
sg_charged: 166
sg_discharged: 227
cs_charged: "Trigonal"
cs_discharged: "Cubic"
formula_charged: "CoO2"
formula_discharged: "LiCoO2"

Energy referensi Li murni: -2.387 eV/atom

V_av = -((-4.2*4) - (-3.8*3) - (1-0)*(-2.387)) / (1*(1-0))
     = -(-16.8 + 11.4 + 2.387) / 1
     = 3.013 V

dV% = |150.3 - 195.5| / min(150.3, 195.5) * 100
    = 45.2 / 150.3 * 100
    = 30.06%

[Capacity & SE dihitung juga]

STEP 3: FEATURIZE FORMULA
──────────────────────────
Formula "LiCoO2" → Matminer

Composition("LiCoO2") = {Li: 0.25, Co: 0.25, O: 0.5}

Features extracted:
  ├─ num_elements: 3
  ├─ stoich_p2: 0.25² + 0.25² + 0.5² = 0.375
  ├─ X_mean: (0.98 + 1.88 + 3.44 + 3.44)/4 = 2.44
  ├─ X_std: std([0.98, 1.88, 3.44, 3.44]) = 1.23
  ├─ X_min: 0.98
  ├─ X_max: 3.44
  ├─ X_range: 2.46
  ├─ atomic_radius_mean: (152 + 135 + 60 + 60)/4 = 101.75
  ├─ Z_mean: (3 + 27 + 8 + 8)/4 = 11.5
  ├─ valence_mean: (1 + 9 + 6 + 6)/4 = 5.5
  ├─ group_mean: (1 + 9 + 16 + 16)/4 = 10.5
  └─ [+ 140 features lainnya]

Formula "CoO2" → Matminer → 151 features juga

STEP 4: COMBINE
────────────────
Untuk 1 row:
  ├─ 10 primary features
  ├─ 151 features dari "LiCoO2"
  ├─ 151 features dari "CoO2"
  └─ Total: 312 features

STEP 5: NORMALIZE & PCA
────────────────────────
312 features → StandardScaler (mean=0, std=1)
              → PCA (keep 120 components, discard 192)
              → 120 PCA components + 4 targets

RESULT: 1 row siap untuk ML model
```

---

## STEP 8: Kenapa Perlu Matminer? (Bukan Manual Query)

### ❌ CARA LAMBAT (Manual Query):
```python
# Untuk setiap material, query ke API
with MPRester(api_key) as mpr:
    for material_id in 1_770_810 material_ids:
        doc = mpr.materials.summary.search(material_ids=[material_id])
        
        # Manual extract dari structure
        for element in doc.structure.composition.elements:
            X = element.X                      # 1 query
            radius = element.atomic_radius     # 1 query
            group = element.group              # 1 query
            # ... dst
        
        # Repeat untuk 151 fitur × 1.77M materials
        # = JUTAAN queries = BERHARI-HARI!
```

**Waktu: 3-5 jam MINIMUM**

### ✅ CARA CEPAT (Matminer):
```python
# Matminer execute offline, punya DB sendiri
from matminer.featurizers.composition import ElementProperty

featurizer = ElementProperty.from_preset("magpie")

# Formula string sudah ada, tinggal compute
for formula_string in dataset["formula"]:  # "LiCoO2"
    comp = Composition(formula_string)
    features = featurizer.featurize(comp)  # INSTANT!

# 151 fitur × 1.77M materials = 30-60 MENIT
```

**Waktu: 30-60 menit**

---

## RINGKASAN SKEMA

```
API Database (MP/AFLOW)
        ↓
     TAHAP 1: Fetch & Find Pairs ✅ DONE
     (Your script sudah lakukan ini)
        ↓
Dataset_BOTH.csv (1.77M × 16 cols)
├─ Basic info (metal, valence, formula)
└─ Computed properties (V_av, dV%, capacity)
        ↓
     TAHAP 2: Extract Composition Features ❌ TODO
     (Gunakan Matminer, ~1 jam)
        ↓
Dataset_Features.csv (1.77M × 308 cols)
├─ 10 primary features
└─ 298 composition features (151×2)
        ↓
     TAHAP 3: Normalize & PCA ❌ TODO
     (StandardScaler + PCA, ~5 menit)
        ↓
ML_Ready.csv (1.68M × 124 cols)
├─ 120 PCA components
└─ 4 target variables
        ↓
     TAHAP 4: Train Model ❌ TODO
     (DNN, ~20 menit)
        ↓
Trained Model
     ↓
Predict V_av & dV% untuk material baru!
```

**Yang Sudah Anda Lakukan: TAHAP 1 ✅**
**Yang Harus Dilanjutkan: TAHAP 2-4 ❌**

