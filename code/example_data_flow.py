"""
CONTOH DATA FLOW - Dari Raw API sampai ML Ready

Ini adalah CONTOH KONKRET bagaimana data mengalir dari awal hingga akhir.
"""

import pandas as pd
import numpy as np
from pymatgen.core import Composition
from matminer.featurizers.composition import (
    Stoichiometry, ElementProperty, ValenceOrbital, IonProperty
)
from matminer.featurizers.base import MultipleFeaturizer

print("=" * 80)
print("CONTOH DATA FLOW: RAW → ML READY")
print("=" * 80)

# ============================================================================
# CONTOH 1: Satu Material dari API
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 1: RAW API DATA (Dari MPRester)")
print("=" * 80)

# Simulasi data dari API
raw_material_1 = {
    "material_id": "mp-123456",
    "formula_pretty": "LiCoO2",
    "composition": {"Li": 1, "Co": 1, "O": 2},
    "volume": 195.5,
    "energy_per_atom": -4.2,
    "nsites": 4,
    "symmetry_number": 227,
    "crystal_system": "Cubic"
}

raw_material_2 = {
    "material_id": "mp-234567",
    "formula_pretty": "CoO2",
    "composition": {"Co": 1, "O": 2},
    "volume": 150.3,
    "energy_per_atom": -3.8,
    "nsites": 3,
    "symmetry_number": 166,
    "crystal_system": "Trigonal"
}

print("\nMaterial 1 (Discharged):")
for k, v in raw_material_1.items():
    print(f"  {k}: {v}")

print("\nMaterial 2 (Charged):")
for k, v in raw_material_2.items():
    print(f"  {k}: {v}")

# ============================================================================
# STAGE 2: Computed Properties (TAHAP 1 - Sudah Anda Lakukan)
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 2: TAHAP 1 - COMPUTED PROPERTIES")
print("=" * 80)

# Simulasi output dari TAHAP 1 (find_pairs + compute_all)
row_stage1 = {
    "metal": "Li",
    "valence": 1,
    "discharged_id": "mp-123456",
    "discharged_formula": "LiCoO2",
    "discharged_sg": 227,
    "discharged_cs": "Cubic",
    "charged_id": "mp-234567",
    "charged_formula": "CoO2",
    "charged_sg": 166,
    "charged_cs": "Trigonal",
    "x1_charged": 0.0,  # No Li in charged
    "x2_discharged": 1.0,  # 1 Li in discharged
    "V_av": 3.013,  # Computed
    "dV_percent": 30.06,  # Computed
    "capacity_mAh_g": 198.62,  # Computed
    "specific_energy_Wh_kg": 625.4,  # Computed
}

print("\n✅ Output dari TAHAP 1 (Dataset_BOTH.csv):")
for k, v in row_stage1.items():
    print(f"  {k}: {v}")

# ============================================================================
# STAGE 3: Extract Composition Features (TAHAP 2 - BELUM ANDA LAKUKAN)
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 3: TAHAP 2 - EXTRACT COMPOSITION FEATURES")
print("=" * 80)

print("\n🔍 Featurizing Discharged Formula: 'LiCoO2'")
print("-" * 80)

featurizer = MultipleFeaturizer([
    Stoichiometry(),
    ElementProperty.from_preset("magpie"),
    ValenceOrbital(props=["frac"]),
    IonProperty(fast=True),
])

# Featurize discharged
comp_disch = Composition("LiCoO2")
features_disch = featurizer.featurize(comp_disch)
labels_disch = featurizer.feature_labels()

print(f"Generated {len(features_disch)} features")
print(f"First 10 features:")
for i, (label, value) in enumerate(zip(labels_disch[:10], features_disch[:10])):
    print(f"  {i+1:2d}. {label:40s}: {value:10.6f}")
print(f"  ... ({len(features_disch)-10} more features)")

# Featurize charged
comp_chg = Composition("CoO2")
features_chg = featurizer.featurize(comp_chg)

print(f"\n🔍 Featurizing Charged Formula: 'CoO2'")
print("-" * 80)
print(f"Generated {len(features_chg)} features (sama, 151 features)")

# Combine ke dalam row
row_stage2 = row_stage1.copy()

# Add discharged features
for label, value in zip(labels_disch, features_disch):
    row_stage2[f"disch__{label}"] = value

# Add charged features
for label, value in zip(labels_disch, features_chg):  # Use same labels
    row_stage2[f"chg__{label}"] = value

print(f"\n✅ Output dari TAHAP 2 (setelah featurization):")
print(f"Total columns: {len(row_stage2)}")
print(f"  - Original 16 columns")
print(f"  - + 151 discharged features (disch__...)")
print(f"  - + 151 charged features (chg__...)")
print(f"  = {len(row_stage2)} columns total")

print(f"\nSample features:")
for key in list(row_stage2.keys())[:5]:
    print(f"  {key}: {row_stage2[key]}")
print("  ...")
for key in list(row_stage2.keys())[-5:]:
    print(f"  {key}: {row_stage2[key]}")

# ============================================================================
# STAGE 4: Create DataFrame (Simulasi 3 rows)
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 4: CONVERT KE DATAFRAME")
print("=" * 80)

# Untuk demo, kita punya 3 rows
row1 = row_stage2.copy()
row1["metal"] = "Li"
row1["V_av"] = 3.013

row2 = row_stage2.copy()
row2["metal"] = "Na"
row2["V_av"] = 2.456

row3 = row_stage2.copy()
row3["metal"] = "Mg"
row3["V_av"] = 1.823

df_with_features = pd.DataFrame([row1, row2, row3])

print(f"\nDataFrame shape: {df_with_features.shape}")
print(f"Columns ({len(df_with_features.columns)}):")
print(f"  - Primary: {len([c for c in df_with_features.columns if not c.startswith('disch__') and not c.startswith('chg__')])}")
print(f"  - Discharged features: {len([c for c in df_with_features.columns if c.startswith('disch__')])}")
print(f"  - Charged features: {len([c for c in df_with_features.columns if c.startswith('chg__')])}")

print(f"\nFirst 5 columns:")
print(df_with_features.iloc[:, :5])

# ============================================================================
# STAGE 5: Normalization & PCA (TAHAP 3 - BELUM ANDA LAKUKAN)
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 5: TAHAP 3 - NORMALIZATION & PCA")
print("=" * 80)

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Separate features and targets
feature_cols = [c for c in df_with_features.columns
                if c.startswith('disch__') or c.startswith('chg__')]
target_cols = ['metal', 'V_av', 'dV_percent', 'capacity_mAh_g', 'specific_energy_Wh_kg']

X = df_with_features[feature_cols].values
y = df_with_features[target_cols]

print(f"\nX shape (features only): {X.shape}")
print(f"  - {X.shape[0]} samples")
print(f"  - {X.shape[1]} features")

# Normalization
print("\n1️⃣  StandardScaler:")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
print(f"   Scaled shape: {X_scaled.shape}")
print(f"   Mean (should be ~0): {X_scaled.mean(axis=0)[:5]}")
print(f"   Std (should be ~1): {X_scaled.std(axis=0)[:5]}")

# PCA
print("\n2️⃣  PCA (reduce 302 → 120 components):")
pca = PCA(n_components=min(120, X_scaled.shape[1]))
X_pca = pca.fit_transform(X_scaled)
evr = pca.explained_variance_ratio_.sum()

print(f"   PCA shape: {X_pca.shape}")
print(f"   Explained variance ratio: {evr:.4f} ({evr*100:.2f}%)")
print(f"   (Paper target: 99.8%)")

# ============================================================================
# STAGE 6: Final ML-Ready Dataset
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 6: FINAL ML-READY DATASET")
print("=" * 80)

# Combine PCA components + targets
df_ml_ready = pd.DataFrame(X_pca, columns=[f"PC{i+1}" for i in range(X_pca.shape[1])])
for col in target_cols:
    df_ml_ready[col] = y[col].values

print(f"\nFinal ML-Ready DataFrame shape: {df_ml_ready.shape}")
print(f"  - {df_ml_ready.shape[0]} samples")
print(f"  - {df_ml_ready.shape[1]} columns")
print(f"    ├─ {X_pca.shape[1]} PCA components (PC1 to PC{X_pca.shape[1]})")
print(f"    └─ {len(target_cols)} target variables")

print(f"\nDataFrame preview:")
print(df_ml_ready.head())

print(f"\nData types:")
print(df_ml_ready.dtypes)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY DATA FLOW")
print("=" * 80)

print("""
┌─────────────────────────────────────────────────────────────────┐
│ RAW API (MP/AFLOW)                                              │
│ ├─ material_id: mp-123456                                       │
│ ├─ formula: "LiCoO2"                                            │
│ ├─ energy: -4.2 eV/atom                                         │
│ └─ volume: 195.5 Å³                                             │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 1: Compute Properties ✅                                  │
│ ├─ Find electrode pairs                                         │
│ ├─ Calculate V_av, dV%, capacity, SE                           │
│ └─ Output: Dataset_BOTH.csv (16 columns)                       │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 2: Extract Features (❌ TODO)                             │
│ ├─ Input: Formula strings ("LiCoO2", "CoO2")                   │
│ ├─ Matminer: 151 features per formula                          │
│ └─ Output: Dataset_Features.csv (312 columns)                  │
│   Time: ~30-60 min for 1.77M pairs                            │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 3: Preprocess (❌ TODO)                                   │
│ ├─ StandardScaler: normalize to mean=0, std=1                  │
│ ├─ PCA: 302 → 120 components (99.8% variance)                  │
│ └─ Output: ML_Ready.csv (124 columns)                          │
│   Time: ~5 min for 1.77M pairs                                │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 4: Train Model (❌ TODO)                                  │
│ ├─ Input: 120 PCA components                                   │
│ ├─ Output: Predict V_av & dV%                                  │
│ └─ Architecture: DNN (7 layers)                                │
│   Time: ~20 min training                                       │
└─────────────────────────────────────────────────────────────────┘
""")

print("\n✅ SUDAH JALAN: TAHAP 1")
print("❌ BELUM: TAHAP 2-4 (total ~1.5-2 jam)")
print("=" * 80)
