"""
Langkah 3: hitung properti elektroda untuk tiap pasangan.

Persamaan (1)-(4) paper:

  V_av = -(E_disch - E_charged - (x2 - x1) * E_M) / (q * (x2 - x1))     (1)

  dV%  = |V_disch - V_charged| / min(V_disch, V_charged) * 100           (2)

  C    = (n * F * 1000) / (3600 * MM)                                    (3)

  SE   = C * V_av                                                        (4)

dengan:
  E_disch, E_charged : energi total sel (commensurate), eV
  E_M                : energi/atom logam aktif murni, eV
  x1, x2             : jumlah ion M pada charged & discharged
  q                  : valensi logam aktif
  V_disch, V_charged : volume sel (commensurate), Å³
  n                  : jumlah elektron ditransfer = q * (x2 - x1)
  F                  : konstanta Faraday
  MM                 : massa molar elektroda discharged, g/mol
"""
from pymatgen.core import Composition

import config


def molar_mass(comp: dict) -> float:
    """Massa molar (g/mol) dari dict komposisi {elemen: jumlah}."""
    formula = "".join(f"{el}{amt}" for el, amt in comp.items())
    return float(Composition(formula).weight)


def compute_properties(pair: dict, e_metal: dict) -> dict | None:
    """
    Hitung V_av, dV%, C, SE untuk satu pasangan.

    `e_metal`: dict {logam: energi/atom murni (eV)}.
    Mengembalikan dict properti, atau None bila tidak terdefinisi.
    """
    metal = pair["metal"]
    q = pair["valence"]
    if metal not in e_metal:
        return None
    E_M = e_metal[metal]

    disch, chg = pair["discharged"], pair["charged"]
    x1, x2 = pair["x1"], pair["x2"]
    dx = x2 - x1
    if dx <= 0:
        return None

    # (1) Voltase rata-rata
    v_av = -(disch["E"] - chg["E"] - dx * E_M) / (q * dx)

    # (2) Persentase perubahan volume
    v_d, v_c = disch["V"], chg["V"]
    denom = min(v_d, v_c)
    if denom <= 0:
        return None
    delta_v = abs(v_d - v_c) / denom * 100.0

    # (3) Kapasitas spesifik (mAh/g). n = elektron ditransfer = q * dx.
    #
    # PENTING: dx (=x2-x1), E, dan V berada dalam basis sel COMMENSURATE,
    # yaitu sel discharged sudah diskalakan faktor f saat pencocokan pasangan
    # (lihat pair_matching.py). Namun disch["comp"] masih komposisi TAK
    # terskala. Karena C bersifat intensif (mAh/g), massa molar harus dibawa
    # ke basis yang sama dengan dx, jika tidak C & SE meleset sebesar f.
    #
    # Faktor skala discharged dipulihkan dari rasio jumlah M terskala
    # (disch["xM"] == x2) terhadap jumlah M tak-terskala (disch["comp"][metal]).
    n_electrons = q * dx
    metal_count_unscaled = disch["comp"].get(metal, 0)
    if metal_count_unscaled <= 0:
        return None
    disch_scale = x2 / metal_count_unscaled
    mm = molar_mass(disch["comp"]) * disch_scale
    if mm <= 0:
        return None
    capacity = (n_electrons * config.FARADAY * 1000.0) / (3600.0 * mm)

    # (4) Energi spesifik (Wh/kg)
    specific_energy = capacity * v_av

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
        "specific_energy_Wh_kg": round(specific_energy, 4),
    }


def compute_all(pairs: list, e_metal: dict) -> list:
    """Hitung properti untuk seluruh pasangan; lewati yang tak terdefinisi."""
    out = []
    for p in pairs:
        props = compute_properties(p, e_metal)
        if props is not None:
            out.append(props)
    return out
