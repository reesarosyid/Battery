"""
Preview dan statistics dari Dataset_BOTH.csv yang baru dibuat.
"""
import pandas as pd
import numpy as np

def show_stats():
    try:
        df = pd.read_csv("data/Dataset_BOTH.csv")
    except FileNotFoundError:
        print("❌ Dataset_BOTH.csv tidak ditemukan. Tunggu proses selesai dulu.")
        return

    print("\n" + "=" * 80)
    print("📊 RAW DATASET STATISTICS (BEFORE FEATURE EXTRACTION)")
    print("=" * 80)

    print(f"\n✅ Shape: {df.shape[0]:,} rows × {df.shape[1]} columns\n")

    print("📋 Kolom:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\n" + "-" * 80)
    print("📊 BASIC STATISTICS")
    print("-" * 80)
    print(df[["metal", "V_av", "dV_percent", "capacity_mAh_g", "specific_energy_Wh_kg"]].describe())

    print("\n" + "-" * 80)
    print("🔬 METAL DISTRIBUTION")
    print("-" * 80)
    metal_counts = df["metal"].value_counts().sort_values(ascending=False)
    for metal, count in metal_counts.items():
        pct = count / len(df) * 100
        print(f"  {metal:2s}: {count:7,} pairs ({pct:5.2f}%)")

    print("\n" + "-" * 80)
    print("⚡ VOLTAGE RANGE")
    print("-" * 80)
    print(f"  Min:    {df['V_av'].min():8.4f} V")
    print(f"  Max:    {df['V_av'].max():8.4f} V")
    print(f"  Mean:   {df['V_av'].mean():8.4f} V")
    print(f"  Median: {df['V_av'].median():8.4f} V")

    print("\n" + "-" * 80)
    print("🔋 CAPACITY RANGE (mAh/g)")
    print("-" * 80)
    print(f"  Min:    {df['capacity_mAh_g'].min():8.4f}")
    print(f"  Max:    {df['capacity_mAh_g'].max():8.4f}")
    print(f"  Mean:   {df['capacity_mAh_g'].mean():8.4f}")
    print(f"  Median: {df['capacity_mAh_g'].median():8.4f}")

    print("\n" + "-" * 80)
    print("💾 SAMPLE DATA (first 10 rows)")
    print("-" * 80)
    print(df[["metal", "discharged_formula", "charged_formula",
              "V_av", "dV_percent", "capacity_mAh_g"]].head(10).to_string())

    print("\n" + "-" * 80)
    print("📁 DATA SUMMARY")
    print("-" * 80)
    print(f"  Total pairs: {len(df):,}")
    print(f"  Total metals: {df['metal'].nunique()}")
    print(f"  Missing values: {df.isnull().sum().sum()}")
    print(f"  File size: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

    print("\n✅ Dataset siap untuk tahap feature extraction!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    show_stats()
