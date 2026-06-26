"""
Langkah 4: featurization untuk model deep learning (Bagian 2.2 & Tabel 1).

Paper menghasilkan fitur berbasis komposisi dengan matminer dari formula
charged & discharged (mengikuti karya sebelumnya, Moses et al. 2021).
Susunan featurizer mengikuti set Ward et al. yang menjadi standar matminer:

    Stoichiometry + ElementProperty(magpie) + ValenceOrbital + IonProperty

Set ini menghasilkan ~132+ fitur per formula. Paper menyebut 151 fitur
per formula (151 x 2 = 302) + 8 fitur primer = 310 fitur, lalu 4 fitur
bernilai nol dibuang -> 306, dinormalisasi, lalu PCA -> 120 komponen.

CATATAN: jumlah persis fitur sedikit bergantung pada versi matminer.
Yang penting prosedurnya identik; jumlah kolom akhir bisa berbeda tipis
dari 151. Sesuaikan daftar featurizer bila ingin mencocokkan persis.
"""
import pandas as pd

from pymatgen.core import Composition

import config


def _build_featurizer():
    from matminer.featurizers.base import MultipleFeaturizer
    from matminer.featurizers.composition import (
        Stoichiometry, ElementProperty, ValenceOrbital, IonProperty,
    )
    return MultipleFeaturizer([
        Stoichiometry(),
        ElementProperty.from_preset("magpie"),
        ValenceOrbital(props=["frac"]),
        IonProperty(fast=True),
    ])


def _comp_from_dict(comp: dict) -> Composition:
    formula = "".join(f"{el}{amt}" for el, amt in comp.items())
    return Composition(formula)


def featurize(pairs_df: pd.DataFrame, pairs_raw: list) -> pd.DataFrame:
    """
    Tambahkan fitur matminer untuk formula charged & discharged.

    `pairs_df`  : DataFrame hasil properties.compute_all (sudah ada target).
    `pairs_raw` : list pasangan dari pair_matching.find_pairs (punya 'comp').
    Mengembalikan DataFrame siap-ML: fitur primer + fitur komposisi + target.
    """
    featurizer = _build_featurizer()

    # Komposisi objek untuk tiap sisi.
    disch_comps = [_comp_from_dict(p["discharged"]["comp"]) for p in pairs_raw]
    chg_comps = [_comp_from_dict(p["charged"]["comp"]) for p in pairs_raw]

    df = pairs_df.copy()
    df["_disch_comp"] = disch_comps
    df["_chg_comp"] = chg_comps

    # Featurize kedua sisi. ignore_errors agar entri aneh tidak menggagalkan.
    df = featurizer.featurize_dataframe(
        df, "_disch_comp", ignore_errors=True, pbar=True)
    labels = featurizer.feature_labels()
    df = df.rename(columns={c: f"disch__{c}" for c in labels})

    df = featurizer.featurize_dataframe(
        df, "_chg_comp", ignore_errors=True, pbar=True)
    df = df.rename(columns={c: f"chg__{c}" for c in labels})

    # --- Fitur primer (Tabel 1 paper, baris 1-8) ---
    df["feat_active_metal"] = df["metal"]
    df["feat_valence"] = df["valence"]
    df["feat_nM_charged"] = df["x1_charged"]
    df["feat_nM_discharged"] = df["x2_discharged"]
    # space group & crystal system charged/discharged sudah ada sebagai kolom
    # discharged_sg, charged_sg, discharged_cs, charged_cs.

    df = df.drop(columns=["_disch_comp", "_chg_comp"])

    # Buang kolom fitur yang seluruhnya nol (paper membuang 4 fitur nol).
    feature_cols = [c for c in df.columns
                    if c.startswith(("disch__", "chg__"))]
    nonzero = [c for c in feature_cols if df[c].abs().sum() != 0]
    zero_dropped = set(feature_cols) - set(nonzero)
    if zero_dropped:
        print(f"[featurize] membuang {len(zero_dropped)} fitur bernilai nol")
    df = df.drop(columns=list(zero_dropped))

    return df


def normalize_and_pca(df: pd.DataFrame, n_components: int = 120):
    """
    Normalisasi fitur lalu PCA (Bagian 2.2). Mengembalikan (X_pca, pipeline).
    Hanya kolom fitur komposisi yang di-PCA; target & metadata tetap.
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.pipeline import Pipeline

    feature_cols = [c for c in df.columns
                    if c.startswith(("disch__", "chg__"))]
    X = df[feature_cols].fillna(0).values

    pipe = Pipeline([
        ("scale", StandardScaler()),
        ("pca", PCA(n_components=min(n_components, X.shape[1]))),
    ])
    X_pca = pipe.fit_transform(X)
    evr = pipe.named_steps["pca"].explained_variance_ratio_.sum()
    print(f"[PCA] {X_pca.shape[1]} komponen, "
          f"variance kumulatif {evr*100:.2f}%")
    return X_pca, pipe
