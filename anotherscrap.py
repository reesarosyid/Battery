import numpy as np
import pandas as pd
from tqdm import tqdm
from mp_api.client import MPRester

api_key = ''
mpr = MPRester(api_key)

CACHE = {}

def extract_features_cached(material_id):
    if material_id in CACHE:
        return CACHE[material_id]
    result = extract_features(material_id)
    CACHE[material_id] = result
    return result

df_raw = pd.read_csv('Dataset.csv')

required_cols = [
    "id_charge",
    "id_discharge",
    "working_ion",
    "average_voltage"
]

for c in required_cols:
  if c not in df_raw.columns:
    raise ValueError(f"kolom {c} tidak di temukan")

df_li = df_raw[df_raw["working_ion"] == "Li"].reset_index(drop=True)

print("jumlah data li : ", len(df_li))

TEST_MODE = False 
TEST_LIMIT = 5    

BATCH_SIZE = 2000        # hasil per batch
START_INDEX = 0         

SAVE_PATH = "./Hasil_Scraping_Dataset_Li_Baterai.csv"

def elemental_stats(structure, attr):
    try:
        vals = []
        for e in structure.composition.elements:
            v = getattr(e, attr, None)
            if v is not None:
                vals.append(v)

        if len(vals) == 0:
            return {}

        vals = np.array(vals)

        return {
            f"{attr}_mean": float(vals.mean()),
            f"{attr}_min": float(vals.min()),
            f"{attr}_max": float(vals.max()),
            f"{attr}_range": float(vals.max() - vals.min()),
            f"{attr}_deviation": float(vals.std())
        }
    except:
        return {}

def stoichiometry_features(structure):
    try:
        comp = structure.composition
        fracs = np.array([comp.get_atomic_fraction(e) for e in comp.elements])

        return {
            "stoich_p2": float(np.sum(fracs ** 2)),
            "stoich_p5": float(np.sum(fracs ** 5)),
            "stoich_p7": float(np.sum(fracs ** 7)),
            "stoich_p10": float(np.sum(fracs ** 10)),
        }
    except:
        return {}

def safe_valence_mean(elems):
    vals = []
    for e in elems:
        try:
            vals.append(e.valence)
        except:
            continue
    if len(vals) == 0:
        return np.nan
    return float(np.mean(vals))

def extract_features(material_id):
    try:
        docs = mpr.materials.summary.search(material_ids=[material_id])
        if len(docs) == 0:
            return None

        doc = docs[0]
        structure = doc.structure
        features = {}

        features["space_group"] = doc.symmetry.number
        features["crystal_system"] = doc.symmetry.crystal_system
        features["bandgap_minimum"] = float(doc.band_gap)

        sv = doc.volume / doc.nsites
        features["specific_volume_mode"] = float(sv)
        features["specific_volume_range"] = 0.0
        features["specific_volume_deviation"] = 0.0

        features.update(elemental_stats(structure, "X"))

        ar = elemental_stats(structure, "atomic_radius")
        features["covalent_radius_mean"] = ar.get("atomic_radius_mean", np.nan)
        features["covalent_radius_deviation"] = ar.get("atomic_radius_deviation", np.nan)

        col = elemental_stats(structure, "group")
        features["column_mean"] = col.get("group_mean", np.nan)
        features["column_max"] = col.get("group_max", np.nan)
        features["column_min"] = col.get("group_min", np.nan)

        elems = structure.composition.elements
        features["total_valence_mean"] = safe_valence_mean(elems)

        features.update(stoichiometry_features(structure))

        return features

    except:
        return None

def extract_pair(row):
    charge = extract_features(row["id_charge"])
    discharge = extract_features(row["id_discharge"])

    if charge is None or discharge is None:
        return None

    out = {
        "id_charge": row["id_charge"],
        "id_discharge": row["id_discharge"],
        "working_ion": "Li",
        "average_voltage": row["average_voltage"],
        "max_delta_volume_per": row["max_delta_volume_per"],
        "capacity_grav": row.get("capacity_grav", np.nan),
        "energy_grav": row.get("energy_grav", np.nan),
    }

    for k, v in charge.items():
        out[f"charge_{k}"] = v

    for k, v in discharge.items():
        out[f"discharge_{k}"] = v

    return out

rows = []

if TEST_MODE:
    end_index = min(START_INDEX + TEST_LIMIT, len(df_li))
else:
    end_index = min(START_INDEX + BATCH_SIZE, len(df_li))

print(f"Processing data {START_INDEX} sampai {end_index}")


for i in tqdm(range(START_INDEX, end_index)):
    r = df_li.iloc[i]

    # charge = extract_features(r["id_charge"])
    # discharge = extract_features(r["id_discharge"])

    charge = extract_features_cached(r["id_charge"])
    discharge = extract_features_cached(r["id_discharge"])

    if charge is None or discharge is None:
        continue

    row = {
        "id_charge": r["id_charge"],
        "id_discharge": r["id_discharge"],
        "working_ion": "Li",
        "average_voltage": r["average_voltage"],
        "max_delta_volume_per": r["max_delta_volume_per"],
    }

    for k, v in charge.items():
        row[f"charge_{k}"] = v
    for k, v in discharge.items():
        row[f"discharge_{k}"] = v

    rows.append(row)

df_out = pd.DataFrame(rows)

if TEST_MODE:
    print("\n=== PREVIEW DATA ===")
    print(df_out)
    print("\nJumlah kolom:", len(df_out.columns))
    print("Nama kolom:", df_out.columns.tolist())
    print("\n** MODE TEST - Data tidak disimpan **")
else:
    if not df_out.empty:
        try:
            df_existing = pd.read_csv(SAVE_PATH)
            df_out = pd.concat([df_existing, df_out], ignore_index=True)
        except:
            pass
    
    df_out.to_csv(SAVE_PATH, index=False)
    print("Batch selesai & tersimpan")
