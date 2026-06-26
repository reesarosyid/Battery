"""
TUTORIAL: Cara Scraping Features dari Materials Project untuk Battery Model

Ini adalah script pembelajaran untuk memahami:
1. Apa saja fitur yang bisa di-scrape dari MP
2. Dari mana fitur-fitur tersebut berasal
3. Bagaimana cara mengekstraknya

WARNING: Script ini LAMBAT karena query per-material.
Untuk production, gunakan matminer (lebih cepat & lebih lengkap).
"""

from mp_api.client import MPRester
from pymatgen.core import Composition
import pandas as pd
import numpy as np

# ============================================================================
# BAGIAN 1: FITUR DARI MP API
# ============================================================================

def scrape_material_features(material_id, api_key):
    """
    Scrape fitur dari satu material di Materials Project.

    Return: dict dengan semua properties yang bisa di-extract
    """

    with MPRester(api_key) as mpr:
        # Query material dengan fields tertentu
        docs = mpr.materials.summary.search(
            material_ids=[material_id],
            fields=[
                "material_id",
                "formula_pretty",
                "composition",
                "structure",           # ← Perlu ini untuk extract lebih banyak info
                "nsites",
                "volume",
                "energy_per_atom",
                "uncorrected_energy_per_atom",
                "symmetry",
                "band_gap",
            ]
        )

        if not docs or len(docs) == 0:
            return None

        doc = docs[0]

        # ====================================================================
        # FITUR DASAR (dari doc fields langsung)
        # ====================================================================
        features = {
            "material_id": str(doc.material_id),
            "formula": doc.formula_pretty,

            # STRUKTUR KRISTAL
            "space_group_number": doc.symmetry.number if doc.symmetry else None,
            "crystal_system": str(doc.symmetry.crystal_system) if doc.symmetry else None,
            "volume": float(doc.volume) if doc.volume else None,
            "nsites": int(doc.nsites),
            "specific_volume": float(doc.volume / doc.nsites) if doc.volume else None,

            # ENERGI (DFT+U)
            "energy_per_atom": float(doc.energy_per_atom) if doc.energy_per_atom else None,
            "uncorrected_energy_per_atom": float(doc.uncorrected_energy_per_atom)
                                          if doc.uncorrected_energy_per_atom else None,
            "total_energy": float(doc.energy_per_atom * doc.nsites)
                           if doc.energy_per_atom else None,

            # ELECTRONIC PROPERTIES
            "band_gap": float(doc.band_gap) if doc.band_gap else None,
        }

        # ====================================================================
        # FITUR DARI COMPOSITION & STRUCTURE
        # ====================================================================

        try:
            comp = doc.composition
            struct = doc.structure

            # Fitur stoichiometry
            fracs = np.array([comp.get_atomic_fraction(e) for e in comp.elements])
            features["num_elements"] = len(comp.elements)
            features["stoich_p2"] = float(np.sum(fracs ** 2))
            features["stoich_p5"] = float(np.sum(fracs ** 5))
            features["stoich_p7"] = float(np.sum(fracs ** 7))
            features["stoich_p10"] = float(np.sum(fracs ** 10))

            # Fitur dari elemen (electronegativity, atomic radius, dll)
            X_values = []  # Electronegativity
            atomic_radius_values = []
            group_values = []
            valence_values = []
            atomic_number_values = []
            atomic_mass_values = []

            for element in comp.elements:
                # Electronegativity (Pauling scale)
                if hasattr(element, 'X'):
                    X_values.append(element.X)

                # Atomic radius (in Ångströms)
                if hasattr(element, 'atomic_radius'):
                    atomic_radius_values.append(element.atomic_radius)

                # Periodic table group
                if hasattr(element, 'group'):
                    group_values.append(element.group)

                # Valence electrons
                try:
                    valence_values.append(element.valence)
                except:
                    pass

                # Atomic number
                if hasattr(element, 'Z'):
                    atomic_number_values.append(element.Z)

                # Atomic mass
                if hasattr(element, 'atomic_mass'):
                    atomic_mass_values.append(element.atomic_mass)

            # Aggregate statistics
            if X_values:
                X_arr = np.array(X_values)
                features["X_mean"] = float(X_arr.mean())
                features["X_min"] = float(X_arr.min())
                features["X_max"] = float(X_arr.max())
                features["X_range"] = float(X_arr.max() - X_arr.min())
                features["X_std"] = float(X_arr.std())

            if atomic_radius_values:
                ar_arr = np.array(atomic_radius_values)
                features["covalent_radius_mean"] = float(ar_arr.mean())
                features["covalent_radius_min"] = float(ar_arr.min())
                features["covalent_radius_max"] = float(ar_arr.max())
                features["covalent_radius_std"] = float(ar_arr.std())

            if group_values:
                group_arr = np.array(group_values)
                features["group_mean"] = float(group_arr.mean())
                features["group_min"] = float(group_arr.min())
                features["group_max"] = float(group_arr.max())

            if atomic_number_values:
                z_arr = np.array(atomic_number_values)
                features["Z_mean"] = float(z_arr.mean())
                features["Z_min"] = float(z_arr.min())
                features["Z_max"] = float(z_arr.max())

            if atomic_mass_values:
                mass_arr = np.array(atomic_mass_values)
                features["mass_mean"] = float(mass_arr.mean())
                features["mass_min"] = float(mass_arr.min())
                features["mass_max"] = float(mass_arr.max())

            if valence_values:
                val_arr = np.array(valence_values)
                features["valence_mean"] = float(val_arr.mean())
                features["valence_min"] = float(val_arr.min())
                features["valence_max"] = float(val_arr.max())

        except Exception as e:
            print(f"  Warning: Gagal extract dari composition/structure: {e}")

        return features


# ============================================================================
# BAGIAN 2: CONTOH PENGGUNAAN & DISPLAY
# ============================================================================

def display_features(features):
    """Display fitur-fitur yang di-scrape dengan kategori."""

    if not features:
        print("❌ Tidak ada fitur")
        return

    print("\n" + "=" * 80)
    print(f"Material: {features.get('formula', 'Unknown')}")
    print("=" * 80)

    # Categorized display
    categories = {
        "🔢 Identifiers": ["material_id", "formula"],

        "🔶 Structure": [
            "space_group_number", "crystal_system", "volume", "nsites",
            "specific_volume"
        ],

        "⚡ Energy (DFT+U)": [
            "energy_per_atom", "uncorrected_energy_per_atom", "total_energy"
        ],

        "🌊 Electronic": [
            "band_gap"
        ],

        "🧪 Stoichiometry": [
            "num_elements", "stoich_p2", "stoich_p5", "stoich_p7", "stoich_p10"
        ],

        "⚛️  Electronegativity (X)": [
            "X_mean", "X_min", "X_max", "X_range", "X_std"
        ],

        "📏 Atomic Radius": [
            "covalent_radius_mean", "covalent_radius_min", "covalent_radius_max",
            "covalent_radius_std"
        ],

        "🔢 Atomic Number": [
            "Z_mean", "Z_min", "Z_max"
        ],

        "⚖️  Atomic Mass": [
            "mass_mean", "mass_min", "mass_max"
        ],

        "🪑 Periodic Group": [
            "group_mean", "group_min", "group_max"
        ],

        "✋ Valence": [
            "valence_mean", "valence_min", "valence_max"
        ]
    }

    for category, feature_names in categories.items():
        has_data = False
        cat_features = []

        for fname in feature_names:
            if fname in features and features[fname] is not None:
                cat_features.append((fname, features[fname]))
                has_data = True

        if has_data:
            print(f"\n{category}")
            for fname, fvalue in cat_features:
                if isinstance(fvalue, float):
                    print(f"  {fname:30s}: {fvalue:12.6f}")
                else:
                    print(f"  {fname:30s}: {fvalue}")

    print("\n" + "=" * 80 + "\n")


# ============================================================================
# BAGIAN 3: DEMONSTRASI (jika ada API key)
# ============================================================================

if __name__ == "__main__":
    # Contoh material ID
    example_ids = [
        "mp-10",        # NaCl
        "mp-12",        # Al2O3
        "mp-3346412",   # Complex oxide
    ]

    print("\n⚠️  DEMONSTRASI - Cara Manual Scraping Features dari Materials Project")
    print("=" * 80)
    print("\nNOTE: Script ini memerlukan MP_API_KEY untuk berjalan.")
    print("Sekarang hanya menampilkan struktur output.\n")

    print("Fitur-fitur yang bisa di-scrape dari MP:")
    print("""
    📌 PRIMARY FEATURES (10 fitur untuk model):
    ───────────────────────────────────────────
    1. Active metal type           ← Manual (Li, Na, K, etc)
    2. Active metal valence        ← Manual lookup
    3. Number of metal in charged  ← Dari composition
    4. Number of metal in discharged ← Dari composition
    5. Space group charged         ← doc.symmetry.number
    6. Space group discharged      ← doc.symmetry.number
    7. Crystal system charged      ← doc.symmetry.crystal_system
    8. Crystal system discharged   ← doc.symmetry.crystal_system
    9. Formula charged             ← doc.formula_pretty
    10. Formula discharged         ← doc.formula_pretty


    🧪 COMPOSITION FEATURES (~151 dari matminer):
    ──────────────────────────────────────────────
    Ini didapat dari chemical FORMULA, bukan direct scraping:

    - Stoichiometry (num_elements, p2, p5, p7, p10, dll)
    - Element properties (electronegativity, atomic radius, group, Z, mass)
    - Valence electrons
    - Crystal structure descriptors

    Matminer library otomatis compute semua ini dari formula!


    ⚡ ENERGI & STRUKTUR (dari DFT):
    ─────────────────────────────────
    - Band gap              ← doc.band_gap
    - Energy per atom       ← doc.energy_per_atom
    - Volume                ← doc.volume
    - Space group           ← doc.symmetry.number
    """)

    print("\n✅ REKOMENDASI:")
    print("""
    1. Jangan scrape semua properties per material (lambat!)
    2. Gunakan matminer untuk 300 composition features
    3. Hanya scrape structure info (space group, crystal system)
    4. Hanya scrape energy/volume untuk primary calculation
    """)

    print("\n📚 Untuk PEMBELAJARAN, lihat:")
    print("  - FEATURE_GUIDE.md (penjelasan lengkap)")
    print("  - anotherscrap.py (manual extraction example)")
    print("  - featurize.py (matminer integration)")
