# 🚀 QUICK START - Complete Scraping Pipeline

**Tutorial lengkap ada di:** `COMPLETE_FEATURES_LIST.md`

---

## 1️⃣ Setup API Key

```bash
# Dapatkan API key dari: https://materialsproject.org/api
export MP_API_KEY="your_api_key_here"
```

## 2️⃣ Install Dependencies

```bash
pip install mp-api pymatgen matminer scikit-learn pandas tqdm
```

## 3️⃣ Run Complete Pipeline

```bash
# Option A: Simple Python run
python screaping.py

# Option B: Using bash script
chmod +x run_scraping.sh
./run_scraping.sh
```

## 4️⃣ Expected Output

```
════════════════════════════════════════════════════════════════════════════════
🚀 COMPLETE SCRAPING PIPELINE
════════════════════════════════════════════════════════════════════════════════

TAHAP 1: FETCH MATERIALS
🔗 Connecting to Materials Project...
🔄 Fetching materials (chunk by chunk)...
  Progress: 1000 materials fetched
  Progress: 2000 materials fetched
  Progress: 3000 materials fetched
✅ Fetched 3,818 materials
💾 Saved to: data/01_raw_mp.json

TAHAP 2: FETCH ELEMENT REFERENCES
🔗 Fetching element reference energies...
  → Li... ✅ -1.9032 eV/atom
  → Na... ✅ -1.3172 eV/atom
  ... (8 more metals)
✅ Fetched 10 element reference energies

TAHAP 3: FIND PAIRS
  → Processing metal: Li...
  → Processing metal: Na...
  ... (8 more metals)
✅ Found 12,456 electrode pairs

TAHAP 4: COMPUTE PROPERTIES
✅ Computed 8,923 properties

TAHAP 5-7: EXTRACT FEATURES + PCA
🔧 Setting up Matminer featurizer...
✅ Featurizer ready: 151 features per formula

📂 Loading properties...
✅ Loaded 8,923 rows

🔄 Extracting discharged features...
  100%|████| 8923/8923 [45:32<00:00, 3.27it/s]
🔄 Extracting charged features...
  100%|████| 8923/8923 [45:12<00:00, 3.31it/s]

📊 Combined shape: (8923, 318)
Removed 10 zero-variance features

Applying PCA (120 components)...
✅ PCA: (8923, 120), Variance: 99.82%

📊 Before filtering: 8923 rows
After filtering: 8654 rows

✅ ML-ready dataset: data/07_ml_ready.csv

════════════════════════════════════════════════════════════════════════════════
✅ PIPELINE COMPLETE!
════════════════════════════════════════════════════════════════════════════════
```

## 5️⃣ Inspect Output Files

```bash
# Check all generated files
ls -lh data/

# Preview final ML-ready dataset
python -c "
import pandas as pd
df = pd.read_csv('data/07_ml_ready.csv')
print('Shape:', df.shape)
print('Columns:', list(df.columns[:10]))
print('Sample:', df.head())
"
```

## 6️⃣ Files Generated

| File | Description |
|------|-------------|
| `data/01_raw_mp.json` | Raw materials dari MP API |
| `data/03_element_ref.json` | Element reference energies |
| `data/04_pairs.json` | Electrode pairs (charged/discharged) |
| `data/05_properties.csv` | Computed V_av, capacity, etc |
| `data/06_features.csv` | With 300+ composition features |
| `data/07_ml_ready.csv` | **ML-READY: 120 PCA components + targets** ⭐ |
| `data/scaler.pkl` | StandardScaler model |
| `data/pca.pkl` | PCA model |

---

## 📊 Next Steps

1. **Use ML-ready dataset:**
   ```python
   import pandas as pd
   df = pd.read_csv('data/07_ml_ready.csv')
   
   # Separate features and targets
   X = df[[col for col in df.columns if col.startswith('PC')]].values
   y = df[['V_av', 'dV_percent']]
   
   # Train your DNN model!
   from tensorflow import keras
   model = keras.Sequential([...])
   model.fit(X, y)
   ```

2. **Make predictions on new data:**
   ```python
   import pickle
   import numpy as np
   
   # Load saved models
   with open('data/scaler.pkl', 'rb') as f:
       scaler = pickle.load(f)
   with open('data/pca.pkl', 'rb') as f:
       pca = pickle.load(f)
   
   # For new composition features X_new
   X_new_scaled = scaler.transform(X_new)
   X_new_pca = pca.transform(X_new_scaled)
   
   # Now use X_new_pca with your trained DNN!
   ```

---

## 🐛 Troubleshooting

| Error | Solution |
|-------|----------|
| `MP_API_KEY not set` | Run: `export MP_API_KEY="your_key"` |
| `ImportError: No module named 'mp_api'` | Run: `pip install mp-api` |
| `Connection timeout` | MP API might be down, wait a bit and retry |
| `Memory error on featurization` | Reduce number of materials, process in batches |
| `PCA variance < 99%` | Increase n_components or filter outliers more |

---

## 📖 Detailed Guide

Untuk penjelasan lengkap setiap tahap, baca:
- **COMPLETE_FEATURES_LIST.md** - Tutorial step-by-step
- **UNDERSTANDING_SUMMARY.txt** - Simple explanation
- **example_data_flow.py** - Concrete examples
