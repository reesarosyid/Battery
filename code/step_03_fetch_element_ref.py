import json
import os
from mp_api.client import MPRester
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def fetch_element_reference_energies(api_key, output_path=config.ELEMENT_REF_PATH):
    """
    Fetch energy per atom untuk tiap metal dalam pure form.
    Diperlukan untuk menghitung voltage.
    """
    print("\nFetching element reference energies...")

    e_metal = {}

    with MPRester(api_key) as mpr:
        for metal in config.ACTIVE_METALS:
            print(f"  {metal}...", end=" ")

            try:
                docs = mpr.materials.summary.search(
                    chemsys=metal,
                    fields=[
                        "material_id",
                        "energy_per_atom",
                        "uncorrected_energy_per_atom",
                        "energy_above_hull",
                    ]
                )

                if not docs:
                    print("No pure metal found")
                    continue

                best = min(docs, key=lambda x: (x.energy_above_hull
                                               if x.energy_above_hull is not None
                                               else 1e9))

                e = (best.uncorrected_energy_per_atom
                    if best.uncorrected_energy_per_atom is not None
                    else best.energy_per_atom)

                e_metal[metal] = float(e)
                print(f"{e:.4f} eV/atom")
            except Exception as e:
                print(f"Error: {e}")
                continue

    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(e_metal, f, indent=2)

    print(f"\nFetched {len(e_metal)} element reference energies")
    print(f"Saved to: {output_path}")

    return e_metal


if __name__ == "__main__":
    import os

    API_KEY = os.environ.get("MP_API_KEY")
    if not API_KEY:
        raise SystemExit("API key not set. Please set MP_API_KEY environment variable.")

    e_metal = fetch_element_reference_energies(API_KEY)

    print(f"\nSample energies:")
    for metal, energy in list(e_metal.items())[:3]:
        print(f"  {metal}: {energy:.4f} eV/atom")
