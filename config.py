# ============================================================================
# config.py - Konfigurasi global
# ============================================================================

# Active metals untuk battery electrodes
ACTIVE_METALS = ["Li", "Na", "K", "Rb", "Cs", "Mg", "Ca", "Al", "Zn", "Y"]

# Valence (muatan ion)
VALENCE = {
    "Li": 1, "Na": 1, "K": 1, "Rb": 1, "Cs": 1,   # monovalen
    "Mg": 2, "Ca": 2, "Zn": 2,                     # divalen
    "Al": 3, "Y": 3,                               # trivalen
}

# Physical constants
FARADAY = 96485.0   # C/mol
RATIO_TOL = 1e-6    # numerical tolerance

# ============================================================================
# Paths
# ----------------------------------------------------------------------------
# Nama kanonik mengikuti alur 8 tahap pipeline. Beberapa modul lama memakai
# nama berbeda untuk artefak yang sama; alias di bawah memastikan SEMUA modul
# (jalur run_pipeline.py maupun jalur step_*/screaping.py) merujuk file yang
# sama dan tidak ada AttributeError. Alias = nilai identik, jadi aman dipakai
# bergantian.
# ============================================================================
DATA_DIR = "Dataset"

# --- Tahap 1-2: data mentah ---
RAW_MP_PATH    = f"{DATA_DIR}/01_raw_mp.json"      # material mentah dari Materials Project
RAW_AFLOW_PATH = f"{DATA_DIR}/02_raw_aflow.json"   # material mentah dari AFLOW

# --- Tahap 3: energi logam aktif murni (E_M untuk Eq. 1) ---
ELEMENT_REF_PATH = f"{DATA_DIR}/03_element_ref.json"

# --- Tahap 4: gabungan MP+AFLOW (sudah dedup) ---
COMBINED_RAW = f"{DATA_DIR}/04_combined_raw.json"

# --- Tahap 5: pasangan elektroda charged<->discharged ---
PAIRS_PATH  = f"{DATA_DIR}/05_pairs.json"          # pasangan gabungan (jalur step_*)
MP_PAIRS    = f"{DATA_DIR}/05_mp_pairs.csv"         # pasangan+properti sumber MP (jalur run_pipeline)
AFLOW_PAIRS = f"{DATA_DIR}/05_aflow_pairs.csv"      # pasangan+properti sumber AFLOW

# --- Tahap 6: properti elektroda (V_av, dV%, C, SE) ---
PROPERTIES_PATH = f"{DATA_DIR}/06_properties.csv"

# --- Tahap 7-8: fitur ML & dataset siap latih ---
FEATURES_PATH = f"{DATA_DIR}/07_features.csv"
ML_READY_PATH = f"{DATA_DIR}/08_ml_ready.csv"

# ----------------------------------------------------------------------------
# Alias kompatibilitas (nama lama yang dipakai modul jalur run_pipeline.py).
# Menunjuk ke file yang sama dengan nama kanonik di atas.
# ----------------------------------------------------------------------------
MP_RAW               = RAW_MP_PATH       # == config.RAW_MP_PATH
AFLOW_RAW            = RAW_AFLOW_PATH     # == config.RAW_AFLOW_PATH
ELEMENT_ENERGY_CACHE = ELEMENT_REF_PATH  # == config.ELEMENT_REF_PATH
FEATURES             = FEATURES_PATH      # == config.FEATURES_PATH
