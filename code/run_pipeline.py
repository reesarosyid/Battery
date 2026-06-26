"""
Orkestrator pipeline lengkap: fetch -> pair matching -> properti -> fitur.

Pemakaian:
    export MP_API_KEY="kunci_anda"

    # 1. Unduh data mentah (MP + referensi logam; AFLOW opsional)
    python run_pipeline.py fetch

    # 2. Cari pasangan & hitung properti -> data/mp_pairs.csv
    python run_pipeline.py pairs --source mp

    # 3. Featurize untuk ML -> data/features.csv
    python run_pipeline.py featurize --source mp

    # atau jalankan semuanya:
    python run_pipeline.py all
"""
import argparse
import json
import os

import pandas as pd

import config
import pair_matching
import properties


def _load(path):
    with open(path) as f:
        return json.load(f)


def step_fetch(args):
    key = os.environ.get("MP_API_KEY") or args.api_key
    if not key:
        raise SystemExit("Set MP_API_KEY untuk mengunduh dari Materials Project.")
    import fetch_mp
    fetch_mp.fetch_element_reference_energy(key)
    fetch_mp.fetch_mp_materials(key)
    if args.with_aflow:
        import fetch_aflow
        fetch_aflow.fetch_aflow_materials()


def step_pairs(args):
    raw_path = config.MP_RAW if args.source == "mp" else config.AFLOW_RAW
    out_path = config.MP_PAIRS if args.source == "mp" else config.AFLOW_PAIRS
    materials = _load(raw_path)
    e_metal = _load(config.ELEMENT_ENERGY_CACHE)

    print(f"[pairs] {len(materials)} material dari {args.source}")
    pairs = pair_matching.find_pairs(materials)
    print(f"[pairs] {len(pairs)} pasangan elektroda ditemukan")

    props = properties.compute_all(pairs, e_metal)
    df = pd.DataFrame(props)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[pairs] {len(df)} instance dgn properti -> {out_path}")

    # Simpan pasangan mentah (dgn komposisi) untuk tahap featurize.
    with open(out_path.replace(".csv", "_raw.json"), "w") as f:
        json.dump(pairs, f, default=str)


def step_featurize(args):
    import featurize
    pairs_csv = config.MP_PAIRS if args.source == "mp" else config.AFLOW_PAIRS
    df = pd.read_csv(pairs_csv)
    with open(pairs_csv.replace(".csv", "_raw.json")) as f:
        pairs_raw = json.load(f)
    feat_df = featurize.featurize(df, pairs_raw)
    feat_df.to_csv(config.FEATURES, index=False)
    print(f"[featurize] {feat_df.shape} -> {config.FEATURES}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("fetch")
    pf.add_argument("--api-key", default=None)
    pf.add_argument("--with-aflow", action="store_true")

    pp = sub.add_parser("pairs")
    pp.add_argument("--source", choices=["mp", "aflow"], default="mp")

    pft = sub.add_parser("featurize")
    pft.add_argument("--source", choices=["mp", "aflow"], default="mp")

    pa = sub.add_parser("all")
    pa.add_argument("--api-key", default=None)
    pa.add_argument("--with-aflow", action="store_true")
    pa.add_argument("--source", choices=["mp", "aflow"], default="mp")

    args = p.parse_args()
    if args.cmd == "fetch":
        step_fetch(args)
    elif args.cmd == "pairs":
        step_pairs(args)
    elif args.cmd == "featurize":
        step_featurize(args)
    elif args.cmd == "all":
        step_fetch(args)
        step_pairs(args)
        step_featurize(args)


if __name__ == "__main__":
    main()
