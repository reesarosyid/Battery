"""
Langkah 1 (sumber AFLOW): unduh & bersihkan material dari AFLOW via AFLUX.

Paper memakai AFLUX (Rose et al. 2017) untuk query AFLOW. AFLUX adalah
REST API sederhana berbasis URL. Kita ambil: komposisi, energi, volume,
space group. AFLOW jauh lebih besar; paginasi wajib.

AFLUX docs: http://aflow.org/API/aflux/
Contoh endpoint: http://aflow.org/API/aflux/?<keywords>,$paging(<n>)
"""
import json
import os
import time

import requests

from pymatgen.core import Composition

import config

AFLUX_BASE = "http://aflow.org/API/aflux/"

# Keyword AFLOW yang kita minta. Lihat daftar lengkap di dokumentasi AFLUX.
#  - compound            : formula (mis. "Nb1S2")
#  - species, composition : elemen & jumlah
#  - enthalpy_cell        : entalpi/energi sel (eV)
#  - volume_cell          : volume sel (Å³)
#  - spacegroup_relax     : nomor space group setelah relaksasi
#  - natoms               : jumlah atom dalam sel
AFLUX_KEYS = ("compound,species,composition,enthalpy_cell,"
              "volume_cell,spacegroup_relax,natoms,nspecies")


def _query_aflux(directive: str, n_per_page: int, page: int, retries: int = 3):
    """Satu permintaan paginasi ke AFLUX. Mengembalikan list dict JSON."""
    url = (f"{AFLUX_BASE}?{AFLUX_KEYS},"
           f"{directive},"
           f"$paging({page},{n_per_page})")
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                print(f"[AFLOW] gagal page {page}: {e}")
                return []
            time.sleep(5 * (attempt + 1))
    return []


def fetch_aflow_materials(out_path: str = config.AFLOW_RAW,
                          n_per_page: int = 1000,
                          max_pages: int = 1000):
    """
    Unduh material dari AFLOW. Karena AFLOW sangat besar, kita batasi pada
    sistem yang mengandung minimal satu logam aktif (lebih relevan & ringan).
    Ubah `directive` ke '' untuk mengunduh seluruh repositori (sangat berat).
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    records = []
    seen = set()

    # Filter: tarik per-logam-aktif agar query terarah & tidak menarik
    # jutaan entri logam-bebas yang tak akan pernah jadi pasangan.
    for metal in config.ACTIVE_METALS:
        directive = f"species(*{metal}*)"  # mengandung logam tsb
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

                    comp_dict = {str(el): int(round(amt))
                                 for el, amt in comp.get_el_amt_dict().items()}
                    sg_number = (int(sg) if isinstance(sg, (int, float))
                                 else None)
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
                        "crystal_system": None,  # diturunkan dari SG bila perlu
                    })
                except Exception:  # noqa: BLE001
                    continue
            print(f"[AFLOW] {metal} page {page}: total terkumpul {len(records)}")
            if len(batch) < n_per_page:
                break  # halaman terakhir
            page += 1
            time.sleep(1)  # sopan terhadap server

    with open(out_path, "w") as f:
        json.dump(records, f)
    print(f"[AFLOW] {len(records)} material disimpan ke {out_path}")
    return records


if __name__ == "__main__":
    fetch_aflow_materials()
