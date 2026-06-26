import json
import pandas as pd
from pymatgen.core import Composition
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def molar_mass(comp):
    """Calculate molar mass dari composition dict."""
    formula = "".join(f"{el}{int(amt)}" for el, amt in comp.items())
    return float(Composition(formula).weight)


def compute_property(pair, e_metal):
    """Compute V_av, dV%, capacity, SE untuk satu pair."""
    metal = pair["metal"]
    q = pair["valence"]

    if metal not in e_metal:
        return None

    E_M = e_metal[metal]
    disch = pair["discharged"]
    chg = pair["charged"]
    x1, x2 = pair["x1"], pair["x2"]
    dx = x2 - x1

    if dx <= 0:
        return None

    v_av = -(disch["E"] - chg["E"] - dx * E_M) / (q * dx)

    denom = min(disch["V"], chg["V"])
    if denom <= 0:
        return None
    delta_v = abs(disch["V"] - chg["V"]) / denom * 100.0

    n_e = q * dx
    # PENTING: dx/E/V berada dalam basis sel COMMENSURATE (sel discharged
    # sudah diskalakan faktor f di step_04), tetapi disch["comp"] masih
    # komposisi TAK terskala. Karena kapasitas bersifat intensif (mAh/g),
    # massa molar harus dibawa ke basis yang sama dengan dx; jika tidak C & SE
    # meleset sebesar f. Faktor skala discharged dipulihkan dari rasio jumlah M
    # terskala (x2) terhadap jumlah M tak-terskala (disch["comp"][metal]).
    metal_count_unscaled = disch["comp"].get(metal, 0)
    if metal_count_unscaled <= 0:
        return None
    disch_scale = x2 / metal_count_unscaled
    mm = molar_mass(disch["comp"]) * disch_scale
    if mm <= 0:
        return None
    capacity = (n_e * config.FARADAY * 1000.0) / (3600.0 * mm)

    se = capacity * v_av

    return {
        "metal": metal,
        "valence": q,
        "discharged_id": disch["id"],
        "discharged_formula": disch["formula"],
        "charged_id": chg["id"],
        "charged_formula": chg["formula"],
        "discharged_sg": disch["sg"],
        "charged_sg": chg["sg"],
        "discharged_cs": disch["cs"],
        "charged_cs": chg["cs"],
        "x1_charged": x1,
        "x2_discharged": x2,
        "V_av": round(v_av, 4),
        "dV_percent": round(delta_v, 4),
        "capacity_mAh_g": round(capacity, 4),
        "specific_energy_Wh_kg": round(se, 4),
    }


def main():
    print("Loading element reference energies...")
    with open(config.ELEMENT_REF_PATH) as f:
        e_metal = json.load(f)

    print("Loading electrode pairs...")
    with open(config.PAIRS_PATH) as f:
        pairs = json.load(f)

    print(f"Loaded {len(pairs):,} pairs")

    print("Computing properties...")
    properties = []
    for i, pair in enumerate(pairs):
        props = compute_property(pair, e_metal)
        if props is not None:
            properties.append(props)

        if (i + 1) % 10000 == 0:
            print(f"  Progress: {i + 1} pairs processed, {len(properties)} valid")

    df = pd.DataFrame(properties)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    df.to_csv(config.PROPERTIES_PATH, index=False)

    print(f"\nComputed {len(properties):,} properties")
    print(f"Saved to: {config.PROPERTIES_PATH}")
    print(f"\nDataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    print(f"\nProperty statistics:")
    print(df[["V_av", "dV_percent", "capacity_mAh_g", "specific_energy_Wh_kg"]].describe())


if __name__ == "__main__":
    main()
