import json
from collections import defaultdict
from fractions import Fraction
from math import gcd
from functools import reduce
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def framework_fingerprint(comp, metal):
    """Fingerprint kerangka non-metal (normalized)."""
    framework = {el: n for el, n in comp.items() if el != metal}
    if not framework:
        return None
    g = reduce(gcd, framework.values())
    if g == 0:
        return None
    norm = {el: n // g for el, n in framework.items()}
    return tuple(sorted(norm.items()))


def commensurate_factor(comp_n, comp_nstar, metal):
    """
    Compute scaling factor f = nA/nA* dari elemen referensi.
    Return (f, is_commensurate).
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

    f = Fraction(int(comp_n[ref]), int(comp_nstar[ref]))

    for el in framework_els:
        if Fraction(int(comp_nstar.get(el, 0))) * f != Fraction(int(comp_n.get(el, 0))):
            return f, False

    return f, True


def find_pairs(materials, metals=None):
    """Cari pasangan elektroda (charged/discharged)."""
    if metals is None:
        metals = config.ACTIVE_METALS

    pairs = []

    for metal in metals:
        print(f"  Processing metal: {metal}...")

        buckets = defaultdict(list)
        for mat in materials:
            fp = framework_fingerprint(mat["composition"], metal)
            if fp is not None:
                buckets[fp].append(mat)

        for fp, group in buckets.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    N = group[i]
                    Nstar = group[j]

                    comp_N = N["composition"]
                    comp_Ns = Nstar["composition"]

                    if (set(comp_N) - {metal}) != (set(comp_Ns) - {metal}):
                        continue

                    f, is_commens = commensurate_factor(comp_N, comp_Ns, metal)
                    if not is_commens or f is None:
                        continue

                    if f > 1:
                        factor = float(f)
                        E_N, V_N = N["energy_cell"], N["volume"]
                        xM_N = comp_N.get(metal, 0)
                        E_Ns = Nstar["energy_cell"] * factor
                        V_Ns = Nstar["volume"] * factor
                        xM_Ns = comp_Ns.get(metal, 0) * factor
                    else:
                        factor = float(Fraction(1) / f)
                        E_N = N["energy_cell"] * factor
                        V_N = N["volume"] * factor
                        xM_N = comp_N.get(metal, 0) * factor
                        E_Ns = Nstar["energy_cell"]
                        V_Ns = Nstar["volume"]
                        xM_Ns = comp_Ns.get(metal, 0)

                    if abs(xM_N - xM_Ns) < config.RATIO_TOL:
                        continue

                    if xM_N > xM_Ns:
                        disch = dict(
                            id=N["id"], formula=N["formula"],
                            comp=comp_N, E=E_N, V=V_N, xM=xM_N,
                            sg=N["space_group"], cs=N["crystal_system"]
                        )
                        chg = dict(
                            id=Nstar["id"], formula=Nstar["formula"],
                            comp=comp_Ns, E=E_Ns, V=V_Ns, xM=xM_Ns,
                            sg=Nstar["space_group"], cs=Nstar["crystal_system"]
                        )
                    else:
                        disch = dict(
                            id=Nstar["id"], formula=Nstar["formula"],
                            comp=comp_Ns, E=E_Ns, V=V_Ns, xM=xM_Ns,
                            sg=Nstar["space_group"], cs=Nstar["crystal_system"]
                        )
                        chg = dict(
                            id=N["id"], formula=N["formula"],
                            comp=comp_N, E=E_N, V=V_N, xM=xM_N,
                            sg=N["space_group"], cs=N["crystal_system"]
                        )

                    pairs.append({
                        "metal": metal,
                        "valence": config.VALENCE[metal],
                        "discharged": disch,
                        "charged": chg,
                        "x1": chg["xM"],
                        "x2": disch["xM"],
                    })

    return pairs


def main():
    print("Loading combined materials...")
    with open(config.COMBINED_RAW) as f:
        materials = json.load(f)

    print(f"Loaded {len(materials):,} materials")

    print("\nFinding electrode pairs...")
    pairs = find_pairs(materials)

    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.PAIRS_PATH, "w") as f:
        json.dump(pairs, f, indent=2)

    print(f"\nFound {len(pairs):,} electrode pairs")
    print(f"Saved to: {config.PAIRS_PATH}")


if __name__ == "__main__":
    main()
