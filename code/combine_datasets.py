"""
Langkah 1: Kombinasikan MP + AFLOW, cari pasangan elektroda, hitung properti.
Simpan hasilnya sebagai Dataset.csv (raw, sebelum feature extraction).

Usage:
    python combine_datasets.py [--source mp|aflow|both]
"""
import json
import argparse
from collections import defaultdict
from fractions import Fraction
from math import gcd
from functools import reduce

import pandas as pd
from pymatgen.core import Composition

import config
import pair_matching
import properties

def load_materials(source="both"):
    """Load materials dari MP, AFLOW, atau keduanya."""
    materials = []

    if source in ["mp", "both"]:
        with open(config.MP_RAW) as f:
            mp_data = json.load(f)
        materials.extend(mp_data)
        print(f"✓ Loaded {len(mp_data):,} materials dari MP")

    if source in ["aflow", "both"]:
        with open(config.AFLOW_RAW) as f:
            aflow_data = json.load(f)
        materials.extend(aflow_data)
        print(f"✓ Loaded {len(aflow_data):,} materials dari AFLOW")

    print(f"✓ TOTAL: {len(materials):,} materials\n")
    return materials


def load_element_energies():
    """Load energi referensi untuk setiap metal."""
    with open(config.ELEMENT_ENERGY_CACHE) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Kombinasikan MP+AFLOW dan cari pasangan elektroda")
    parser.add_argument("--source", choices=["mp", "aflow", "both"], default="both",
                       help="Sumber data (default: both)")
    args = parser.parse_args()

    print("=" * 70)
    print("TAHAP 1: LOAD DATA & FIND PAIRS")
    print("=" * 70)
    print()

    # Load data
    materials = load_materials(source=args.source)
    e_metal = load_element_energies()

    # Find pairs
    print("🔍 Mencari pasangan elektroda...")
    pairs = pair_matching.find_pairs(materials)
    print(f"✓ Ditemukan {len(pairs):,} pasangan elektroda\n")

    # Compute properties
    print("📊 Menghitung properti (V_av, dV%, capacity, specific_energy)...")
    props_list = properties.compute_all(pairs, e_metal)
    print(f"✓ Computed {len(props_list):,} properti (yang valid)\n")

    # Convert to DataFrame
    df = pd.DataFrame(props_list)

    # Save to CSV
    output_path = f"data/Dataset_{args.source.upper()}.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Simpan ke: {output_path}\n")

    # Display statistics
    print("=" * 70)
    print("RAW DATA STATISTICS")
    print("=" * 70)
    print(f"\n📈 Shape: {df.shape[0]:,} rows × {df.shape[1]} columns\n")

    print("📋 Kolom:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\n📊 Data Types:")
    print(df.dtypes)

    print("\n📈 Basic Statistics:")
    print(df[["metal", "V_av", "dV_percent", "capacity_mAh_g", "specific_energy_Wh_kg"]].describe().T)

    print("\n🔬 Metal Distribution:")
    metal_counts = df["metal"].value_counts().sort_index()
    for metal, count in metal_counts.items():
        print(f"  {metal}: {count:,} pairs")

    print("\n📊 Sample Data (5 baris pertama):")
    print(df[["metal", "discharged_formula", "charged_formula",
              "V_av", "dV_percent", "capacity_mAh_g"]].head())

    print(f"\n✅ Selesai! Raw dataset tersimpan di: {output_path}")
    print(f"   Siap untuk tahap 2: feature extraction\n")


if __name__ == "__main__":
    main()
