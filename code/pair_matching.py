"""
Langkah 2 (INTI): cari pasangan elektroda charged <-> discharged.

Mereplikasi algoritma pada Fig. 1 & Bagian 2.1 paper.

Untuk tiap pasangan material (N, N*):
  1. Spesies atom sama, ATAU berbeda hanya pada logam aktif M.
  2. Rasio jumlah tiap spesies non-M di N dan N* konsisten (commensurate);
     hanya jumlah M yang boleh berbeda.
  3. Skala unit cell yang lebih kecil dengan faktor f = nA/nA* (atau
     kebalikannya) sehingga kerangka non-M kedua material setara. Energi
     & volume per unit cell ikut diskalakan.
  4. Material dengan jumlah M lebih banyak = discharged; lainnya = charged.

Optimasi: alih-alih membandingkan O(n^2) seluruh pasangan (tidak praktis
untuk >100k material), material dikelompokkan berdasarkan "fingerprint
kerangka" = formula non-M yang dinormalisasi. Pasangan hanya dibandingkan
dalam grup yang sama. Hasilnya setara dengan brute force tetapi jauh lebih
cepat.
"""
from collections import defaultdict
from fractions import Fraction
from math import gcd
from functools import reduce

import config


def _framework_fingerprint(comp: dict, metal: str):
    """
    Fingerprint kerangka non-M yang dinormalisasi.

    Mengembalikan tuple terurut ((elemen, rasio_int), ...) di mana rasio
    dinormalisasi ke bilangan bulat terkecil (dibagi GCD). Dua material
    dengan fingerprint sama punya kerangka non-M yang commensurate.

    Mengembalikan None bila material tidak punya kerangka non-M (mis. logam
    murni) -> tidak bisa jadi pasangan interkalasi yang bermakna.
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
    set_a = set(comp_a) - {metal}
    set_b = set(comp_b) - {metal}
    return set_a == set_b


def _commensurate_factor(comp_n: dict, comp_nstar: dict, metal: str):
    """
    Hitung faktor skala f = nA/nA* memakai elemen kerangka referензi A.

    Kembalikan (f, framework_match) di mana framework_match True bila SELURUH
    elemen non-M memiliki rasio yang sama dengan f (benar-benar commensurate).
    f dikembalikan sebagai Fraction agar eksak.
    """
    framework_els = (set(comp_n) | set(comp_nstar)) - {metal}
    if not framework_els:
        return None, False

    # Pilih elemen referensi A: elemen non-M pertama yang ada di kedua sisi.
    ref = None
    for el in sorted(framework_els):
        if comp_n.get(el, 0) > 0 and comp_nstar.get(el, 0) > 0:
            ref = el
            break
    if ref is None:
        return None, False

    f = Fraction(comp_n[ref], comp_nstar[ref])

    # Verifikasi seluruh elemen non-M konsisten dgn faktor f.
    for el in framework_els:
        n = comp_n.get(el, 0)
        nstar = comp_nstar.get(el, 0)
        # Setelah skala N* dengan f, jumlah el harus cocok: n == nstar * f
        if Fraction(nstar) * f != Fraction(n):
            return f, False
    return f, True


def find_pairs(materials: list, metals=None):
    """
    Cari semua pasangan elektroda valid di antara `materials`.

    `materials`: list dict dgn kunci 'id','composition','volume',
                 'energy_cell','space_group','crystal_system'.
    Mengembalikan list dict pasangan (belum dihitung properti).
    """
    if metals is None:
        metals = config.ACTIVE_METALS

    pairs = []

    for metal in metals:
        # Kelompokkan material berdasarkan fingerprint kerangka untuk logam ini.
        buckets = defaultdict(list)
        for mat in materials:
            comp = mat["composition"]
            fp = _framework_fingerprint(comp, metal)
            if fp is None:
                continue
            buckets[fp].append(mat)

        for fp, group in buckets.items():
            n_items = len(group)
            if n_items < 2:
                continue
            # Bandingkan tiap pasangan dalam grup (i < j) - O(k^2) per grup,
            # tetapi k jauh lebih kecil dari total material.
            for i in range(n_items):
                N = group[i]
                comp_N = N["composition"]
                for j in range(i + 1, n_items):
                    Nstar = group[j]
                    comp_Ns = Nstar["composition"]

                    # Syarat 1: hanya berbeda pada logam M
                    if not _has_only_metal_difference(comp_N, comp_Ns, metal):
                        continue

                    # Syarat 2 & 3: kerangka commensurate, hitung faktor f
                    f, ok = _commensurate_factor(comp_N, comp_Ns, metal)
                    if not ok or f is None:
                        continue

                    # Skala unit cell yang lebih kecil agar setara.
                    # f = nA(N)/nA(N*).
                    #  - f > 1  => N lebih besar; skala N* (energi,volume,M) x f
                    #  - f < 1  => skala N x (1/f)
                    if f > 1:
                        scale_for = "Nstar"
                        factor = f
                    else:
                        scale_for = "N"
                        factor = Fraction(1) / f

                    factor = float(factor)
                    if scale_for == "Nstar":
                        E_N = N["energy_cell"]
                        V_N = N["volume"]
                        xM_N = comp_N.get(metal, 0)
                        E_Ns = Nstar["energy_cell"] * factor
                        V_Ns = Nstar["volume"] * factor
                        xM_Ns = comp_Ns.get(metal, 0) * factor
                        mat_N, mat_Ns = N, Nstar
                    else:
                        E_N = N["energy_cell"] * factor
                        V_N = N["volume"] * factor
                        xM_N = comp_N.get(metal, 0) * factor
                        E_Ns = Nstar["energy_cell"]
                        V_Ns = Nstar["volume"]
                        xM_Ns = comp_Ns.get(metal, 0)
                        mat_N, mat_Ns = N, Nstar

                    # Setelah penyetaraan, jumlah M harus berbeda.
                    if abs(xM_N - xM_Ns) < config.RATIO_TOL:
                        continue

                    # Syarat 4: M lebih banyak = discharged.
                    if xM_N > xM_Ns:
                        disch = dict(id=mat_N["id"], formula=mat_N["formula"],
                                     comp=comp_N, E=E_N, V=V_N, xM=xM_N,
                                     sg=mat_N["space_group"],
                                     cs=mat_N["crystal_system"])
                        chg = dict(id=mat_Ns["id"], formula=mat_Ns["formula"],
                                   comp=comp_Ns, E=E_Ns, V=V_Ns, xM=xM_Ns,
                                   sg=mat_Ns["space_group"],
                                   cs=mat_Ns["crystal_system"])
                    else:
                        disch = dict(id=mat_Ns["id"], formula=mat_Ns["formula"],
                                     comp=comp_Ns, E=E_Ns, V=V_Ns, xM=xM_Ns,
                                     sg=mat_Ns["space_group"],
                                     cs=mat_Ns["crystal_system"])
                        chg = dict(id=mat_N["id"], formula=mat_N["formula"],
                                   comp=comp_N, E=E_N, V=V_N, xM=xM_N,
                                   sg=mat_N["space_group"],
                                   cs=mat_N["crystal_system"])

                    pairs.append({
                        "metal": metal,
                        "valence": config.VALENCE[metal],
                        "discharged": disch,
                        "charged": chg,
                        "x1": chg["xM"],      # jumlah M pada charged (lebih sedikit)
                        "x2": disch["xM"],    # jumlah M pada discharged (lebih banyak)
                    })

    return pairs
