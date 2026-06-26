"""
Langkah 1 (sumber MP): unduh & bersihkan material dari Materials Project.

Paper memakai legacy MAPI (sudah pensiun Sept 2025). Modul ini memakai
client resmi terbaru `mp-api`. Karena database MP terus diperbarui, daftar
material yang didapat TIDAK akan identik dengan snapshot 2022 milik paper.

Properti yang diambil (mengikuti paper, Bagian 2.1):
- material_id, formula, komposisi unit cell (elemen + jumlah atom)
- space group (nomor) & crystal system
- energi total per unit cell (DFT+U) & volume unit cell
- nsites (jumlah atom)

Catatan energi: paper memakai "energi DFT+U dari unit cell". Pada API baru,
`energy_per_atom` (uncorrected/raw) dikalikan nsites memberi energi total
unit cell. Untuk konsistensi termodinamika voltase, gunakan energi yang
sama (raw DFT energy) untuk material DAN untuk logam referensi.
"""
import json
import os

from pymatgen.core import Composition

import config


def fetch_mp_materials(api_key: str, out_path: str = config.MP_RAW,
                       chunk_size: int = 1000):
    """
    Unduh semua material inorganik dari MP, buang non-solid & duplikat,
    lalu simpan sebagai JSON.

    Memerlukan: pip install mp-api
    API key: https://next-gen.materialsproject.org/api
    """
    from mp_api.client import MPRester

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    records = []

    with MPRester(api_key) as mpr:
        # summary.search mengembalikan ringkasan untuk seluruh material.
        # Kita minta hanya field yang diperlukan agar transfer ringan.
        docs = mpr.materials.summary.search(
            fields=[
                "material_id",
                "formula_pretty",
                "composition",          # pymatgen Composition (unit cell tereduksi)
                "composition_reduced",
                "nsites",
                "volume",
                "energy_per_atom",      # eV/atom (corrected). Lihat catatan di bawah.
                "uncorrected_energy_per_atom",
                "symmetry",             # berisi number (space group) & crystal_system
                "is_metal",
                "theoretical",
            ],
            chunk_size=chunk_size,
        )

    seen = set()  # untuk buang duplikat berdasarkan komposisi+spacegroup
    for d in docs:
        try:
            comp = d.composition                      # komposisi unit cell penuh
            nsites = d.nsites
            volume = d.volume
            # Energi total unit cell = energi/atom * jumlah atom.
            # Gunakan uncorrected agar konsisten dgn referensi logam murni.
            e_per_atom = (d.uncorrected_energy_per_atom
                          if d.uncorrected_energy_per_atom is not None
                          else d.energy_per_atom)
            if e_per_atom is None or volume is None:
                continue
            energy_cell = e_per_atom * nsites

            sg_number = d.symmetry.number if d.symmetry else None
            crystal_system = (str(d.symmetry.crystal_system)
                              if d.symmetry else None)

            # Buang struktur non-solid: paper hanya ingin solid-state.
            # MP umumnya berisi kristal; saring entri tanpa volume valid.
            if volume <= 0:
                continue

            # Komposisi unit cell sebagai dict {elemen: jumlah}
            comp_dict = {str(el): int(round(amt))
                         for el, amt in comp.get_el_amt_dict().items()}

            # Kunci dedup: formula tereduksi + space group
            key = (comp.reduced_formula, sg_number)
            if key in seen:
                continue
            seen.add(key)

            records.append({
                "id": str(d.material_id),
                "formula": d.formula_pretty,
                "composition": comp_dict,
                "nsites": int(nsites),
                "volume": float(volume),       # volume unit cell penuh (Å³)
                "energy_cell": float(energy_cell),  # eV, unit cell penuh
                "space_group": sg_number,
                "crystal_system": crystal_system,
            })
        except Exception as e:  # noqa: BLE001 - lewati entri rusak, lanjut
            continue

    with open(out_path, "w") as f:
        json.dump(records, f)
    print(f"[MP] {len(records)} material solid disimpan ke {out_path}")
    return records


def fetch_element_reference_energy(api_key: str,
                                   out_path: str = config.ELEMENT_ENERGY_CACHE):
    """
    Ambil energi DFT per atom logam aktif dalam bentuk MURNI (E_M).

    Diperlukan untuk persamaan voltase (Eq. 1 paper). Untuk tiap logam,
    cari fasa elemental paling stabil (energy_above_hull terendah) lalu
    pakai uncorrected_energy_per_atom.
    """
    from mp_api.client import MPRester

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    e_metal = {}
    with MPRester(api_key) as mpr:
        for m in config.ACTIVE_METALS:
            docs = mpr.materials.summary.search(
                chemsys=m,
                fields=["material_id", "uncorrected_energy_per_atom",
                        "energy_per_atom", "energy_above_hull"],
            )
            if not docs:
                print(f"[WARN] tidak ada fasa murni untuk {m}")
                continue
            best = min(docs, key=lambda x: (x.energy_above_hull
                                            if x.energy_above_hull is not None
                                            else 1e9))
            e = (best.uncorrected_energy_per_atom
                 if best.uncorrected_energy_per_atom is not None
                 else best.energy_per_atom)
            e_metal[m] = float(e)
            print(f"[E_M] {m}: {e:.4f} eV/atom  ({best.material_id})")

    with open(out_path, "w") as f:
        json.dump(e_metal, f, indent=2)
    return e_metal


if __name__ == "__main__":
    import sys
    key = os.environ.get("MP_API_KEY") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not key:
        raise SystemExit("Set MP_API_KEY atau berikan API key sebagai argumen.")
    fetch_element_reference_energy(key)
    fetch_mp_materials(key)
