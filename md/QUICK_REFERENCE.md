# ⚡ QUICK REFERENCE: Features untuk Battery Model

## 📊 Yang Anda Punya Sekarang

✅ **Dataset_BOTH.csv** (1.77M pairs)
- Column 1-16: All primary features + 4 computed properties

```
metal | valence | discharged_id | discharged_formula | ... | V_av | dV% | capacity | SE
------|---------|---------------|-------------------|-----|------|-----|----------|----
Li    | 1       | mp-123456     | LiCoO2             | ... | 3.14 | 15.2| 198.6    | 625
```

## ❌ Yang Belum Ada

**Composition Features** (300 fitur dari matminer)

Perlu di-extract dari chemical formula menggunakan matminer:
- 151 fitur per charged formula
- 151 fitur per discharged formula
- Total: 302 fitur

---

## 🔍 3 SUMBER FITUR

### 1️⃣ MANUAL/CONFIG (1 fitur)
```python
# active metal type
metal = "Li"  # dari ACTIVE_METALS list
```

### 2️⃣ DIRECT FROM API (9 fitur)
```python
# Dari doc object (MPRester)
doc.formula_pretty          # "LiCoO2"
doc.symmetry.number         # 227
doc.symmetry.crystal_system # "Cubic"
doc.composition             # {"Li": 1, "Co": 1, "O": 2}
doc.nsites                  # 4
doc.volume                  # 195.5

# Computed from composition
n_metal = composition.get(metal, 0)  # 1
```

### 3️⃣ DERIVED FROM FORMULA (300 fitur)
```python
# Gunakan matminer pada formula string!
from matminer.featurizers.composition import (
    Stoichiometry, ElementProperty, ValenceOrbital, IonProperty
)

featurizer = MultipleFeaturizer([
    Stoichiometry(),
    ElementProperty.from_preset("magpie"),
    ValenceOrbital(props=["frac"]),
    IonProperty(fast=True),
])

for formula in ["LiCoO2", "CoO2", ...]:
    comp = Composition(formula)
    features_151 = featurizer.featurize(comp)
```

---

## 🎯 FITUR BREAKDOWN

### **10 Primary Features** (Sudah di Dataset_BOTH.csv)

| # | Feature | From | Type |
|---|---------|------|------|
| 1 | active_metal | Config | str |
| 2 | valence | Lookup | int |
| 3 | n_metal_charged | Composition | float |
| 4 | n_metal_discharged | Composition | float |
| 5 | sg_charged | API | int |
| 6 | sg_discharged | API | int |
| 7 | cs_charged | API | str |
| 8 | cs_discharged | API | str |
| 9 | formula_charged | API | str |
| 10 | formula_discharged | API | str |

### **300+ Composition Features** (Perlu matminer)

From matminer on each formula:

**Example for "LiCoO2":**
- Stoichiometry: num_elements=3, stoich_p2=..., stoich_p5=...
- Electronegativity: X_mean=2.45, X_std=1.23, X_range=2.46
- Atomic radius: ar_mean=95.3, ar_std=47.5
- Atomic number: Z_mean=12.3, Z_min=3, Z_max=27
- Valence: val_mean=5.33, val_min=1, val_max=9
- Periodic group: group_mean=10, group_min=1, group_max=16
- + ~100 more features

---

## 📈 PIPELINE

```
Dataset_BOTH.csv (1.77M × 16 cols)
         ↓
    [Matminer Featurization]
    Add 300 composition features
         ↓
Final_Dataset.csv (1.77M × 316 cols)
         ↓
    [Normalization + PCA]
    StandardScaler → PCA(120 components)
         ↓
ML-Ready Data (1.77M × 124 cols)
  - 120 PCA components
  - 4 target variables (V_av, dV%, capacity, SE)
```

---

## ⚙️ IMPLEMENTATION STEPS

### Step 1: Add matminer features (30-60 min)
```python
from pymatgen.core import Composition
from matminer.featurizers.composition import (
    Stoichiometry, ElementProperty, ValenceOrbital, IonProperty
)

# For each row in Dataset_BOTH.csv:
# 1. Parse charged_formula → Composition
# 2. Featurize → 151 features
# 3. Parse discharged_formula → Composition
# 4. Featurize → 151 features
# 5. Add all 302 columns to CSV
```

### Step 2: Normalize (1 min)
```python
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)
```

### Step 3: PCA (5 min)
```python
from sklearn.decomposition import PCA
pca = PCA(n_components=120)
X_pca = pca.fit_transform(X_scaled)
print(f"Variance explained: {pca.explained_variance_ratio_.sum():.4f}")
# Should be ~0.998 (99.8%)
```

### Step 4: Filter outliers
```python
# Remove samples with:
# - V_av < -13 or V_av > 13 (low voltage region, not for battery)
# - dV% > 500 (too much volume change)
# Should remove ~5% of data
```

---

## 💾 FILE REFERENCES

📄 **FEATURE_GUIDE.md** - Lengkap penjelasan fitur
📄 **FEATURES_COMPARISON.txt** - Visual comparison
📄 **scraping_explained.py** - Code example
📄 **featurize.py** - Matminer integration code (already in repo)

---

## ❓ FAQ

**Q: Apakah saya perlu scrape semua properties per material?**
A: TIDAK! Hanya perlu formula string + basic info. Matminer handle sisanya.

**Q: Kenapa 300 features dan bukan langsung pakai formula?**
A: Formula string tidak bisa digunakan langsung di ML. Harus convert ke numerical features dulu.

**Q: Berapa lama featurization untuk 1.77M pairs?**
A: ~30-60 menit (tergantung CPU). Matminer tidak parallelizable, jadi sequential.

**Q: Apakah 120 PCA components cukup?**
A: Ya, paper menggunakan 120 components untuk menangkap 99.8% variance.

**Q: Bisa langsung train model dengan 306 features tanpa PCA?**
A: Bisa, tapi worse performance. PCA mengurangi noise & overfitting.

---

## 🚀 NEXT ACTION

Buat script untuk:
1. Load Dataset_BOTH.csv
2. Featurize setiap formula dengan matminer
3. Append 300 columns ke CSV
4. Normalize & PCA
5. Save final dataset

**Estimated time: 1-2 jam total**
