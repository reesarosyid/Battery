# 📊 PANDUAN FITUR: MATERIALS PROJECT vs BATTERY MODEL

## 🎯 SUMMARY

Menurut paper Moses et al. (2022), battery model memerlukan **310 fitur** yang terdiri dari:
- **10 primary features** → dari MP/AFLOW API langsung
- **300 composition features** → derived dari chemical formula menggunakan matminer library

Anda **TIDAK perlu scrape semua properties** dari MP API. Hanya perlu:
1. **Basic structure info** (space group, crystal system)
2. **Chemical formula** (yang kemudian di-featurize)

---

## 📥 FITUR DARI MATERIALS PROJECT API

### **Fitur yang Tersedia (dapat di-scrape):**

```python
from mp_api.client import MPRester

mpr = MPRester(api_key)
docs = mpr.materials.summary.search(
    fields=[
        "material_id",              # ✓ ID material
        "formula_pretty",           # ✓ Chemical formula (pretty format)
        "composition",              # ✓ Chemical composition dict
        "structure",                # ✓ Crystal structure (pymatgen Structure)
        "nsites",                   # ✓ Number of atoms in unit cell
        "volume",                   # ✓ Unit cell volume (Ų)
        "energy_per_atom",          # ✓ DFT energy per atom (eV/atom)
        "uncorrected_energy_per_atom",  # ✓ Raw DFT energy
        "symmetry",                 # ✓ Symmetry info (space group, crystal system)
        "band_gap",                 # ✓ Bandgap (eV)
    ]
)

# Dari structure (pymatgen.core.Structure), bisa extract:
for doc in docs:
    doc.symmetry.number              # Space group number (1-230)
    doc.symmetry.crystal_system      # Crystal system (Cubic, Hexagonal, etc)
    doc.composition.elements         # List of elements
    doc.band_gap                     # Bandgap energy
    doc.structure.volume             # Volume dari structure
```

**Catatan:** Anotherscrap.py extract properti tambahan via structure object:
```python
doc.band_gap                        # Bandgap
doc.volume / doc.nsites             # Specific volume
structure.composition.elements[i].X  # Electronegativity (Pauling scale)
structure.composition.elements[i].atomic_radius  # Atomic radius
structure.composition.elements[i].group  # Periodic table group
```

---

## 📋 FITUR YANG DIPERLUKAN MENURUT PAPER

### **Tahap 1: Primary Features (10 fitur)**

Diambil langsung dari **electrodes pair** dan **materials properties**:

| # | Feature | Source | Type | Contoh |
|----|---------|--------|------|--------|
| 1 | Active metal type | Manual (Li, Na, K, dll) | categorical | "Li" |
| 2 | Active metal valence | Manual lookup | int | 1, 2, 3 |
| 3 | Number of metal in charged | Composition dict | float | 1.0 |
| 4 | Number of metal in discharged | Composition dict | float | 2.0 |
| 5 | Space group charged | `symmetry.number` | int | 227 |
| 6 | Space group discharged | `symmetry.number` | int | 166 |
| 7 | Crystal system charged | `symmetry.crystal_system` | str | "Cubic" |
| 8 | Crystal system discharged | `symmetry.crystal_system` | str | "Trigonal" |
| 9 | Chemical formula charged | `formula_pretty` | str | "LiCoO2" |
| 10 | Chemical formula discharged | `formula_pretty` | str | "CoO2" |

**Notebook Anda sudah menghitung:**
- ✅ metal, valence (dari config)
- ✅ x1_charged, x2_discharged (dari composition)
- ✅ discharged_sg, charged_sg (dari symmetry.number)
- ✅ discharged_cs, charged_cs (dari symmetry.crystal_system)
- ✅ discharged_formula, charged_formula (dari formula_pretty)

---

### **Tahap 2: Composition-based Features (300 fitur)**

Dari **chemical formula**, gunakan **matminer library** untuk extract:

```python
from matminer.featurizers.composition import (
    Stoichiometry,              # Stoichiometry features
    ElementProperty,            # Element properties (atomic number, mass, etc)
    ValenceOrbital,             # Valence orbital info
    IonProperty,                # Ion properties
)

featurizer = MultipleFeaturizer([
    Stoichiometry(),
    ElementProperty.from_preset("magpie"),
    ValenceOrbital(props=["frac"]),
    IonProperty(fast=True),
])

# Ini generate ~151 features per chemical formula
# Untuk charged + discharged = 302 features
```

**Contoh fitur matminer (dari 151):**

```
Stoichiometry:
  - Number of elements
  - Fraction of each element p-block, d-block, f-block
  - Electronegativity (mean, max, min, std)

ElementProperty (Magpie):
  - Atomic number (mean, max, min)
  - Atomic mass (mean, max, min)
  - Electronegativity (mean, std, range)
  - First ionization energy
  - Valence electrons (mean, max, min)
  - Covalent radius (mean, std, range)
  - Thermal conductivity

ValenceOrbital:
  - Valence electron configuration fractions

IonProperty:
  - Ion radii
  - Ionic potentials
```

---

## ⚙️ PIPELINE YANG SEHARUSNYA

```
┌─────────────────────────────────────────────────────────────┐
│ TAHAP 1: DATA MINING (Sudah Anda lakukan)                  │
├─────────────────────────────────────────────────────────────┤
│ ✓ Fetch materials dari MP/AFLOW                             │
│ ✓ Find electrode pairs (charged/discharged)                │
│ ✓ Compute: V_av, dV%, capacity, specific_energy            │
│ ✓ Save: Dataset_BOTH.csv (1.77M pairs)                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ TAHAP 2: FEATURE EXTRACTION (Feature Engineering)           │
├─────────────────────────────────────────────────────────────┤
│ Input: Dataset_BOTH.csv                                     │
│ ├─ Primary features (10) ← sudah ada                        │
│ └─ Composition features (300) ← matminer pada formula       │
│                                                              │
│ Process:                                                    │
│ 1. Untuk setiap charged & discharged formula               │
│ 2. Featurize dengan matminer → 151 features per formula    │
│ 3. Combine: 10 + 302 = 312 features                        │
│ 4. Remove 4 zero-value features → 308 features            │
│ 5. Normalize (StandardScaler)                              │
│ 6. PCA: 308 → 120 components (99.8% variance)             │
│                                                              │
│ Output: Final_Dataset.csv (1.77M × 124 columns)            │
│         [target(4) + primary(10) + PCA(120)]              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ TAHAP 3: MODEL TRAINING                                     │
├─────────────────────────────────────────────────────────────┤
│ ✓ Filter outliers (V_av: -13 to 13V, dV% < 500%)          │
│ ✓ Split: 90% train, 10% test                               │
│ ✓ Build DNN model (7 layers, 120 input features)          │
│ ✓ Train: predict V_av & dV%                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 PERBANDINGAN: ANOTHERSCRAP.PY vs YANG ANDA BUTUHKAN

### **Apa yang anotherscrap.py lakukan:**

```python
# Extract dari MP struktur object
doc.symmetry.number                 # Space group ✓
doc.symmetry.crystal_system         # Crystal system ✓
doc.band_gap                        # Bandgap (tapi tidak digunakan di paper!)

# Extract dari composition elements
element.X                           # Electronegativity ✓
element.atomic_radius               # Atomic radius ✓
element.group                       # Periodic table group ✓
element.valence                     # Valence electrons ✓

# Stoichiometry
sum(atomic_fractions ** 2)          # Stoich_p2 ✓
sum(atomic_fractions ** 5)          # Stoich_p5 ✓
```

**Masalah:** anotherscrap.py manually extract fitur dari `element` object, padahal **matminer library sudah otomatis** mengkalkulasi ini!

---

## 💡 REKOMENDASI UNTUK ANDA

### **Opsi A: Gunakan matminer (RECOMMENDED)**

**Kelebihan:**
- ✅ Sudah built-in, tinggal pakai
- ✅ Konsisten dengan paper
- ✅ 151 fitur teruji (bandah dari matminer Magpie preset)
- ✅ Lebih cepat (batched processing)

**Script:**
```python
from matminer.featurizers.composition import (
    Stoichiometry, ElementProperty, ValenceOrbital, IonProperty
)

featurizer = MultipleFeaturizer([
    Stoichiometry(),
    ElementProperty.from_preset("magpie"),
    ValenceOrbital(props=["frac"]),
    IonProperty(fast=True),
])

# Featurize formula
comp = Composition("LiCoO2")
features = featurizer.featurize(comp)
feature_labels = featurizer.feature_labels()
```

### **Opsi B: Manual scrape via MPRester (Untuk Belajar)**

Jika Anda ingin **paham cara kerjanya**, scrape ini:

```python
from mp_api.client import MPRester

mpr = MPRester(api_key)
docs = mpr.materials.summary.search(material_ids=[id_list])

for doc in docs:
    # Primary info
    sg = doc.symmetry.number
    cs = str(doc.symmetry.crystal_system)
    
    # Dari structure object (perlu download structure)
    struct = doc.structure
    comp = struct.composition
    
    # Extract element properties
    for element in comp.elements:
        X = element.X                      # Electronegativity (Pauling)
        z = element.Z                      # Atomic number
        ar = element.atomic_radius         # Atomic radius
        group = element.group              # Periodic table group
```

**Masalah:** 
- Lambat (perlu query per material)
- Manual, rentan kesalahan
- Tidak lengkap (missing properties dari matminer)

---

## 📊 CONTOH: Matminer Features (151 fitur)

```python
from matminer.featurizers.composition import ElementProperty
from pymatgen.core import Composition

featurizer = ElementProperty.from_preset("magpie")
comp = Composition("Li2CoO2")

features = featurizer.featurize(comp)
labels = featurizer.feature_labels()

print(f"Generated {len(features)} features:")
for label, value in zip(labels[:10], features[:10]):
    print(f"  {label}: {value:.4f}")

# Output example:
# MagpieData mean Number ...
# MagpieData mean Number ...
# mean X (Pauling electronegativity): 2.456
# std X (Pauling electronegativity): 0.834
# min X (Pauling electronegativity): 1.0
# max X (Pauling electronegativity): 3.44
# ...
```

---

## ✅ CHECKLIST: APA YANG SUDAH ANDA MILIKI

✅ Dataset_BOTH.csv dengan 1.77M pairs
✅ 10 primary features (sudah ada di CSV)
- metal, valence
- x1_charged, x2_discharged
- discharged_sg, charged_sg, discharged_cs, charged_cs
- discharged_formula, charged_formula

❌ 300 composition features (belum ada)
❌ Normalized & PCA (belum ada)

---

## 🚀 NEXT STEP

1. **Pilih approach** (matminer vs manual scrape)
2. **Buat script** untuk add 300 composition features ke Dataset_BOTH.csv
3. **Apply normalisasi & PCA** → 120 komponen
4. **Filter outliers** (V_av: -13 to 13V, dV% < 500%)
5. **Train DNN model** untuk prediksi V_av & dV%

**Waktu estimasi:**
- Matminer featurization: 30-60 menit untuk 1.77M pairs
- PCA: 5 menit
- Model training: 10-20 menit

---

## 📚 REFERENSI

**Paper:** Moses et al. (2022), "Accelerating the discovery of battery electrode materials 
through data mining and deep learning models", J. Power Sources 546, 231977

**Libraries:**
- Materials Project API: `mp_api`
- Matminer: `matminer.featurizers.composition`
- PyMatGen: `pymatgen.core`
- Scikit-learn: `sklearn.decomposition.PCA`

