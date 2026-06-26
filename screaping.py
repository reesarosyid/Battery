import json
import os
import requests
import time
from collections import defaultdict
from fractions import Fraction
from math import gcd
from functools import reduce
from mp_api.client import MPRester
from pymatgen.core import Composition
import config

# AFLOW API constants
AFLUX_BASE = "http://aflow.org/API/aflux/"
AFLUX_KEYS = ("compound,species,composition,enthalpy_cell,"
              "volume_cell,spacegroup_relax,natoms,nspecies")


def crystal_system_from_sg(sg_number):
    """Turunkan crystal system dari nomor space group (1-230).

    Dipakai untuk material AFLOW yang hanya mengembalikan nomor space group
    tanpa label crystal system, padahal paper memakai crystal system sebagai
    fitur (Table 1, no. 7-8). Rentang mengikuti konvensi IUCr.
    """
    if not isinstance(sg_number, int) or sg_number < 1 or sg_number > 230:
        return None
    for upper, name in (
        (2,   "Triclinic"),
        (15,  "Monoclinic"),
        (74,  "Orthorhombic"),
        (142, "Tetragonal"),
        (167, "Trigonal"),
        (194, "Hexagonal"),
        (230, "Cubic"),
    ):
        if sg_number <= upper:
            return name
    return None

def _parse_mp_doc(doc):
    """Ubah satu SummaryDoc MP -> dict ringkas, atau None bila non-solid."""
    energy_per_atom = (doc.uncorrected_energy_per_atom
                       if doc.uncorrected_energy_per_atom is not None
                       else doc.energy_per_atom)
    # Filter non-solid (paper Bagian 2.1): MP summary tidak menandai
    # solid/non-solid eksplisit, jadi pakai proxy volume valid + energi ada.
    if energy_per_atom is None or doc.volume is None or doc.volume <= 0:
        return None
    comp_dict = {str(el): int(round(amt))
                 for el, amt in doc.composition.get_el_amt_dict().items()}
    return {
        "id": str(doc.material_id),
        "formula": doc.formula_pretty,
        "composition": comp_dict,
        "nsites": int(doc.nsites),
        "volume": float(doc.volume),
        "energy_cell": float(energy_per_atom * doc.nsites),
        "space_group": doc.symmetry.number if doc.symmetry else None,
        "crystal_system": (str(doc.symmetry.crystal_system)
                           if doc.symmetry else None),
    }


def fetch_mp_materials(api_key, output_path=config.RAW_MP_PATH,
                       batch_size=2000, limit=None):
    """Fetch inorganic materials dari Materials Project dgn checkpoint+resume.

    Strategi tahan-putus:
      1. Ambil daftar `material_id` saja (1 field ringan -> cepat).
      2. Tarik detail per-batch (`batch_size` id sekali query); simpan
         checkpoint `<output>.partial` SETIAP batch. Kalau proses terputus,
         jalankan lagi -> otomatis lanjut dari id yang belum terambil.

    Args:
        batch_size: jumlah material_id per query detail.
        limit:      batasi total material (mode test cepat). None = semua.
    """
    fields = ["material_id", "formula_pretty", "composition", "nsites",
              "volume", "energy_per_atom", "uncorrected_energy_per_atom",
              "symmetry"]

    os.makedirs(config.DATA_DIR, exist_ok=True)
    ckpt_path = output_path + ".partial"

    # Resume dari checkpoint bila ada.
    materials, done_ids = [], set()
    if os.path.exists(ckpt_path):
        with open(ckpt_path) as f:
            materials = json.load(f)
        done_ids = {m["id"] for m in materials}
        print(f"Resume: {len(done_ids):,} material sudah ada di checkpoint")

    with MPRester(api_key) as mpr:
        print("\nMengambil daftar material_id (ringan)...")
        all_ids = [str(d.material_id)
                   for d in mpr.materials.summary.search(fields=["material_id"])]
        if limit:
            all_ids = all_ids[:limit]
        todo = [i for i in all_ids if i not in done_ids]
        print(f"Total {len(all_ids):,} material, sisa {len(todo):,} diambil")

        t0 = time.time()
        for start in range(0, len(todo), batch_size):
            batch = todo[start:start + batch_size]
            docs = mpr.materials.summary.search(material_ids=batch, fields=fields)
            for doc in docs:
                try:
                    rec = _parse_mp_doc(doc)
                    if rec is not None:
                        materials.append(rec)
                except Exception:
                    continue

            # Checkpoint tiap batch -> aman bila putus.
            with open(ckpt_path, "w") as f:
                json.dump(materials, f)

            done = start + len(batch)
            rate = done / max(time.time() - t0, 1e-9)
            eta = (len(todo) - done) / max(rate, 1e-9)
            print(f"  {done:,}/{len(todo):,} | {len(materials):,} solid | "
                  f"{rate:.0f}/s | ETA {eta/60:.1f} min")

    with open(output_path, "w") as f:
        json.dump(materials, f, indent=2)
    if os.path.exists(ckpt_path):
        os.remove(ckpt_path)

    print(f"\nFetched {len(materials):,} materials")
    print(f"Saved to: {output_path}")
    return materials

def _query_aflux(directive: str, n_per_page: int, page: int, retries: int = 3):
    """Satu permintaan paginasi ke AFLUX dengan retry mechanism."""
    parts = [AFLUX_KEYS]
    if directive:                       # directive kosong = seluruh repositori
        parts.append(directive)
    parts.append(f"$paging({page},{n_per_page})")
    url = f"{AFLUX_BASE}?{','.join(parts)}"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"[AFLOW] gagal page {page}: {e}")
                return []
            time.sleep(5 * (attempt + 1))
    return []

def fetch_aflow_materials(out_path: str = config.AFLOW_RAW,
                          n_per_page: int = 1000,
                          max_pages: int = 1000,
                          restrict_to_active_metals: bool = True):
    """
    Fetch materials dari AFLOW.

    Args:
        out_path: Path untuk simpan JSON
        n_per_page: Jumlah materials per halaman
        max_pages: Max halaman per query
        restrict_to_active_metals:
            True  -> query per logam aktif (`species(*M*)`). Ringan & terarah,
                     TETAPI elektroda charged yang sudah tidak mengandung logam
                     aktif (mis. CoO2 sebagai pasangan charged dari LiCoO2)
                     TIDAK akan terambil, sehingga sebagian pasangan dari AFLOW
                     hilang. Konsisten dengan code/fetch_aflow.py.
            False -> tarik SELURUH repositori AFLOW (sangat berat, jutaan
                     entri) agar endmember charged tanpa logam aktif ikut
                     terambil. Paling setia ke metodologi paper (Bagian 2.1).

    Returns:
        list of materials
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    records = []
    seen = set()

    # Daftar (label, directive) yang akan di-query.
    if restrict_to_active_metals:
        tasks = [(m, f"species(*{m}*)") for m in config.ACTIVE_METALS]
    else:
        tasks = [("ALL", "")]  # directive kosong = seluruh repositori

    for label, directive in tasks:
        print(f"Fetching AFLOW materials [{label}]...")
        page = 1

        while page <= max_pages:
            batch = _query_aflux(directive, n_per_page, page)
            if not batch:
                break

            for d in batch:
                try:
                    comp_str = d.get("compound")
                    if not comp_str:
                        continue

                    comp = Composition(comp_str)
                    volume = float(d.get("volume_cell", 0) or 0)
                    energy = d.get("enthalpy_cell")
                    sg = d.get("spacegroup_relax")

                    if energy is None or volume <= 0:
                        continue
                    
                    
                    # Parse composition
                    comp_dict = {str(el): int(round(amt))
                                 for el, amt in comp.get_el_amt_dict().items()}
                    sg_number = (int(sg) if isinstance(sg, (int, float))
                                else None)
                    
                    # Avoid duplicates
                    key = (comp.reduced_formula, sg_number)
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    records.append({
                        "id": d.get("auid") or comp_str,
                        "formula": comp.reduced_formula,
                        "composition": comp_dict,
                        "nsites": int(d.get("natoms", sum(comp_dict.values()))),
                        "volume": volume,
                        "energy_cell": float(energy),
                        "space_group": sg_number,
                        "crystal_system": crystal_system_from_sg(sg_number),
                    })
                except Exception:
                    continue
            print(f"  {label} page {page}: {len(batch)} records, total: {len(records)}")
            
            if len(batch) < n_per_page:
                break  # Last page
            
            page += 1
            time.sleep(1)  # Be nice to server
    
    # Save to JSON
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nFetched {len(records):,} AFLOW materials")
    print(f"Saved to: {out_path}")
    
    return records

def combine_materials(mp_path, aflow_path, output_path):
    """Combine MP & AFLOW materials, remove duplicates."""
    
    with open(mp_path) as f:
        mp_materials = json.load(f)
    
    with open(aflow_path) as f:
        aflow_materials = json.load(f)
    
    print(f"MP materials: {len(mp_materials):,}")
    print(f"AFLOW materials: {len(aflow_materials):,}")
    
    # Deduplicate by (formula, space_group)
    seen = {}
    combined = []
    
    for mat in mp_materials + aflow_materials:
        key = (mat["formula"], mat["space_group"])
        if key not in seen:
            seen[key] = True
            combined.append(mat)
    
    print(f"Combined (deduplicated): {len(combined):,} materials")
    
    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2)
    
    return combined


def fetch_element_reference_energies(api_key, output_path=config.ELEMENT_REF_PATH):
    """Fetch energi/atom logam aktif murni (E_M) untuk Eq. 1 paper.

    Untuk tiap logam, ambil fasa elemental paling stabil (energy_above_hull
    terendah) lalu pakai uncorrected_energy_per_atom agar konsisten dgn
    energi material (raw DFT).
    """
    print("\nFetching element reference energies (E_M)...")
    e_metal = {}
    with MPRester(api_key) as mpr:
        for metal in config.ACTIVE_METALS:
            try:
                docs = mpr.materials.summary.search(
                    chemsys=metal,
                    fields=["material_id", "energy_per_atom",
                            "uncorrected_energy_per_atom", "energy_above_hull"],
                )
                if not docs:
                    print(f"  {metal}: tidak ada fasa murni")
                    continue
                best = min(docs, key=lambda x: (x.energy_above_hull
                                                if x.energy_above_hull is not None
                                                else 1e9))
                e = (best.uncorrected_energy_per_atom
                     if best.uncorrected_energy_per_atom is not None
                     else best.energy_per_atom)
                e_metal[metal] = float(e)
                print(f"  {metal}: {e:.4f} eV/atom ({best.material_id})")
            except Exception as ex:
                print(f"  {metal}: error {ex}")
                continue

    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(e_metal, f, indent=2)
    print(f"Saved E_M to: {output_path}")
    return e_metal


# ===========================================================================
# STEP: CARI PASANGAN charged <-> discharged (Fig. 1 & Bagian 2.1 paper)
# ===========================================================================
def _framework_fingerprint(comp: dict, metal: str):
    """Fingerprint kerangka non-M ternormalisasi (rasio int dibagi GCD).

    Dua material dgn fingerprint sama -> kerangka non-M commensurate.
    None bila tak punya kerangka non-M (mis. logam murni).
    """
    framework = {el: n for el, n in comp.items() if el != metal}
    if not framework:
        return None
    counts = list(framework.values())
    g = reduce(gcd, counts)
    if g == 0:
        return None
    norm = {el: n // g for el, n in framework.items()}
    return tuple(sorted(norm.items()))


def _has_only_metal_difference(comp_a: dict, comp_b: dict, metal: str) -> bool:
    """Set elemen A & B sama, atau hanya berbeda pada `metal`."""
    return (set(comp_a) - {metal}) == (set(comp_b) - {metal})


def _commensurate_factor(comp_n: dict, comp_nstar: dict, metal: str):
    """Faktor skala eksak f = nA/nA* memakai elemen kerangka referensi A.

    Kembalikan (f, ok) di mana ok True bila SEMUA elemen non-M konsisten
    dgn f (benar-benar commensurate).
    """
    framework_els = (set(comp_n) | set(comp_nstar)) - {metal}
    if not framework_els:
        return None, False
    ref = None
    for el in sorted(framework_els):
        if comp_n.get(el, 0) > 0 and comp_nstar.get(el, 0) > 0:
            ref = el
            break
    if ref is None:
        return None, False
    f = Fraction(comp_n[ref], comp_nstar[ref])
    for el in framework_els:
        if Fraction(comp_nstar.get(el, 0)) * f != Fraction(comp_n.get(el, 0)):
            return f, False
    return f, True


def find_pairs(materials: list, metals=None):
    """Cari semua pasangan elektroda valid (Fig. 1 paper).

    materials: list dict dgn 'id','composition','volume','energy_cell',
               'space_group','crystal_system'. Mengembalikan list pasangan.
    """
    if metals is None:
        metals = config.ACTIVE_METALS
    pairs = []

    for metal in metals:
        buckets = defaultdict(list)
        for mat in materials:
            fp = _framework_fingerprint(mat["composition"], metal)
            if fp is None:
                continue
            buckets[fp].append(mat)

        for fp, group in buckets.items():
            n_items = len(group)
            if n_items < 2:
                continue
            for i in range(n_items):
                N = group[i]
                comp_N = N["composition"]
                for j in range(i + 1, n_items):
                    Nstar = group[j]
                    comp_Ns = Nstar["composition"]

                    if not _has_only_metal_difference(comp_N, comp_Ns, metal):
                        continue
                    f, ok = _commensurate_factor(comp_N, comp_Ns, metal)
                    if not ok or f is None:
                        continue

                    # Skala unit cell yang lebih kecil agar setara. f=nA(N)/nA(N*)
                    if f > 1:                       # N lebih besar -> skala N*
                        factor = float(f)
                        E_N, V_N = N["energy_cell"], N["volume"]
                        xM_N = comp_N.get(metal, 0)
                        E_Ns = Nstar["energy_cell"] * factor
                        V_Ns = Nstar["volume"] * factor
                        xM_Ns = comp_Ns.get(metal, 0) * factor
                    else:                            # N* lebih besar -> skala N
                        factor = float(Fraction(1) / f)
                        E_N = N["energy_cell"] * factor
                        V_N = N["volume"] * factor
                        xM_N = comp_N.get(metal, 0) * factor
                        E_Ns, V_Ns = Nstar["energy_cell"], Nstar["volume"]
                        xM_Ns = comp_Ns.get(metal, 0)

                    if abs(xM_N - xM_Ns) < config.RATIO_TOL:
                        continue  # jumlah M harus berbeda setelah penyetaraan

                    side_N = dict(id=N["id"], formula=N["formula"], comp=comp_N,
                                  E=E_N, V=V_N, xM=xM_N,
                                  sg=N["space_group"], cs=N["crystal_system"])
                    side_Ns = dict(id=Nstar["id"], formula=Nstar["formula"],
                                   comp=comp_Ns, E=E_Ns, V=V_Ns, xM=xM_Ns,
                                   sg=Nstar["space_group"],
                                   cs=Nstar["crystal_system"])

                    # M lebih banyak = discharged
                    disch, chg = ((side_N, side_Ns) if xM_N > xM_Ns
                                  else (side_Ns, side_N))
                    pairs.append({
                        "metal": metal,
                        "valence": config.VALENCE[metal],
                        "discharged": disch,
                        "charged": chg,
                        "x1": chg["xM"],      # M pada charged (lebih sedikit)
                        "x2": disch["xM"],    # M pada discharged (lebih banyak)
                    })
    return pairs


# ===========================================================================
# STEP: COMPUTE PROPERTIES (Eq. 1-4 paper)
# ===========================================================================
def _molar_mass(comp: dict) -> float:
    formula = "".join(f"{el}{amt}" for el, amt in comp.items())
    return float(Composition(formula).weight)


def compute_properties(pair: dict, e_metal: dict):
    """Hitung V_av, dV%, C, SE untuk satu pasangan (Eq. 1-4). None bila invalid."""
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

    # (3) Kapasitas spesifik (mAh/g). n = q * dx. MM dibawa ke basis
    # commensurate yg sama dgn dx (lihat pair_matching: discharged diskalakan).
    n_electrons = q * dx
    metal_count_unscaled = disch["comp"].get(metal, 0)
    if metal_count_unscaled <= 0:
        return None
    disch_scale = x2 / metal_count_unscaled
    mm = _molar_mass(disch["comp"]) * disch_scale
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


def compute_all(pairs: list, e_metal: dict, output_path=config.PROPERTIES_PATH):
    """Hitung properti seluruh pasangan; kembalikan (pair, props) yang valid.

    Pasangan dikembalikan bersama props agar featurization per-pasangan
    selalu sejajar (1:1) dgn baris properti.
    """
    import pandas as pd

    valid = []
    for p in pairs:
        props = compute_properties(p, e_metal)
        if props is not None:
            valid.append((p, props))

    if output_path:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        pd.DataFrame([pr for _, pr in valid]).to_csv(output_path, index=False)
        print(f"\nComputed properties: {len(valid):,} pasangan valid")
        print(f"Saved to: {output_path}")
    return valid


# ===========================================================================
# STEP: COMPOSITION FEATURE EXTRACTION per-pasangan (matminer, Tabel 1 paper)
# ===========================================================================
def _comp_from_dict(comp: dict) -> Composition:
    formula = "".join(f"{el}{amt}" for el, amt in comp.items())
    return Composition(formula)


def featurize_pairs(pairs_with_props, output_path=config.FEATURES_PATH):
    """Composition-based features (matminer) untuk formula charged & discharged.

    Sesuai paper (Bagian 2.2 & Tabel 1): fitur komposisi dihitung untuk KEDUA
    sisi tiap pasangan (prefix `disch__` & `chg__`), digabung dgn fitur primer
    (logam aktif, valensi, jumlah M, space group & crystal system kedua sisi)
    dan target (V_av, dV%). Featurizer = set Ward et al. (standar matminer).

    `pairs_with_props`: list (pair, props) dari compute_all.
    """
    import pandas as pd
    from matminer.featurizers.base import MultipleFeaturizer
    from matminer.featurizers.composition import (
        Stoichiometry, ElementProperty, ValenceOrbital, IonProperty,
    )

    if not pairs_with_props:
        print("\n[featurize_pairs] tidak ada pasangan valid, dilewati.")
        return None

    pairs = [p for p, _ in pairs_with_props]
    props = [pr for _, pr in pairs_with_props]

    featurizer = MultipleFeaturizer([
        Stoichiometry(),
        ElementProperty.from_preset("magpie"),
        ValenceOrbital(props=["frac"]),
        IonProperty(fast=True),
    ])
    labels = featurizer.feature_labels()

    df = pd.DataFrame(props)
    df["_disch_comp"] = [_comp_from_dict(p["discharged"]["comp"]) for p in pairs]
    df["_chg_comp"] = [_comp_from_dict(p["charged"]["comp"]) for p in pairs]

    print(f"\nFeaturizing {len(df):,} pasangan (discharged + charged)...")
    df = featurizer.featurize_dataframe(df, "_disch_comp",
                                        ignore_errors=True, pbar=True)
    df = df.rename(columns={c: f"disch__{c}" for c in labels})
    df = featurizer.featurize_dataframe(df, "_chg_comp",
                                        ignore_errors=True, pbar=True)
    df = df.rename(columns={c: f"chg__{c}" for c in labels})
    df = df.drop(columns=["_disch_comp", "_chg_comp"])

    # Buang kolom fitur yang seluruhnya nol (paper membuang fitur nol).
    feat_cols = [c for c in df.columns if c.startswith(("disch__", "chg__"))]
    zero_cols = [c for c in feat_cols if df[c].abs().sum() == 0]
    if zero_cols:
        print(f"Membuang {len(zero_cols)} fitur bernilai nol")
        df = df.drop(columns=zero_cols)

    os.makedirs(config.DATA_DIR, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"ML-ready dataset: {len(df):,} baris, "
          f"{len(feat_cols) - len(zero_cols)} fitur komposisi")
    print(f"Saved to: {output_path}")
    return df


def main():
    API_KEY = os.environ.get("MP_API_KEY")

    if not API_KEY:
        raise SystemExit("API key not set. Please set MP_API_KEY environment variable.")

    print(f"\nActive metals: {', '.join(config.ACTIVE_METALS)}")
    print(f"Valence: {config.VALENCE}")

    print("\n" + "="*80)
    print("STEP 1: FETCH MATERIALS (MP + AFLOW)")
    print("="*80)
    fetch_mp_materials(API_KEY)
    fetch_aflow_materials()
    combined = combine_materials(
        config.RAW_MP_PATH, config.AFLOW_RAW, config.COMBINED_RAW)
    e_metal = fetch_element_reference_energies(API_KEY)

    print("\n" + "="*80)
    print("STEP 2: CARI PASANGAN charged <-> discharged")
    print("="*80)
    pairs = find_pairs(combined)
    with open(config.PAIRS_PATH, "w") as f:
        json.dump(pairs, f)
    print(f"Ditemukan {len(pairs):,} pasangan -> {config.PAIRS_PATH}")

    print("\n" + "="*80)
    print("STEP 3: COMPUTE PROPERTIES (V_av, dV%, C, SE)")
    print("="*80)
    pairs_with_props = compute_all(pairs, e_metal)

    print("\n" + "="*80)
    print("STEP 4: COMPOSITION FEATURE EXTRACTION (matminer)")
    print("="*80)
    featurize_pairs(pairs_with_props)


if __name__ == "__main__":
    main()