"""
Uji logika inti tanpa perlu akses API.

Memverifikasi:
1. Pencocokan pasangan menemukan pasangan yang benar & menentukan
   charged/discharged dengan tepat.
2. Penyetaraan (commensurate scaling) untuk sel berbeda ukuran benar.
3. Rumus V_av/dV%/C/SE mereproduksi nilai yang dihitung tangan.
"""
import pair_matching
import properties


def test_simple_pair_nbS2_naNbS2():
    """NbS2 (charged) <-> NaNbS2 (discharged), Na monovalen.

    Energi disetel agar V_av target = 1.80 V (lih. Table 4 baris 3, DFT+U).
    E_Na murni = -1.30 eV/atom; E_NbS2 = -20.0 eV.
    V_av = -(E_disch - E_chg - (x2-x1)*E_M) / (q*(x2-x1))
         = -(E_disch - (-20) - 1*(-1.3)) / 1  = 1.8
      => E_disch = -20 - 1.3 - 1.8 = -23.1
    """
    materials = [
        {"id": "NbS2", "formula": "NbS2",
         "composition": {"Nb": 1, "S": 2},
         "nsites": 3, "volume": 60.0, "energy_cell": -20.0,
         "space_group": 160, "crystal_system": "trigonal"},
        {"id": "NaNbS2", "formula": "NaNbS2",
         "composition": {"Na": 1, "Nb": 1, "S": 2},
         "nsites": 4, "volume": 67.4, "energy_cell": -23.1,
         "space_group": 166, "crystal_system": "trigonal"},
    ]
    pairs = pair_matching.find_pairs(materials, metals=["Na"])
    assert len(pairs) == 1, f"harusnya 1 pasangan, dapat {len(pairs)}"
    p = pairs[0]
    assert p["discharged"]["id"] == "NaNbS2"   # lebih banyak Na
    assert p["charged"]["id"] == "NbS2"
    assert p["x1"] == 0 and p["x2"] == 1

    e_metal = {"Na": -1.30}
    props = properties.compute_properties(p, e_metal)
    assert abs(props["V_av"] - 1.80) < 1e-3, props["V_av"]
    # dV% = |67.4-60|/60 *100 = 12.333...
    assert abs(props["dV_percent"] - 12.3333) < 1e-2, props["dV_percent"]
    print("OK  pair sederhana NbS2/NaNbS2:",
          f"V_av={props['V_av']} dV%={props['dV_percent']} "
          f"C={props['capacity_mAh_g']} SE={props['specific_energy_Wh_kg']}")


def test_commensurate_scaling():
    """Kerangka berbeda ukuran sel: Li2(TiS2) vs (TiS2)2 -> harus diskalakan.

    N  = Li2Ti2S4 (sudah 2x TiS2 + 2 Li), V=120, E=-46
    N* = TiS2     (1x),                   V=55,  E=-20
    Kerangka N* harus dikali 2 agar setara: V*->110, E*->-40.
    x2 (disch, Li2Ti2S4) = 2 ; x1 (charged TiS2 x2) = 0.
    dV% = |120 - 110|/110 *100 = 9.0909...
    """
    materials = [
        {"id": "TiS2", "formula": "TiS2",
         "composition": {"Ti": 1, "S": 2},
         "nsites": 3, "volume": 55.0, "energy_cell": -20.0,
         "space_group": 164, "crystal_system": "trigonal"},
        {"id": "Li2Ti2S4", "formula": "Li2Ti2S4",
         "composition": {"Li": 2, "Ti": 2, "S": 4},
         "nsites": 8, "volume": 120.0, "energy_cell": -46.0,
         "space_group": 166, "crystal_system": "trigonal"},
    ]
    pairs = pair_matching.find_pairs(materials, metals=["Li"])
    assert len(pairs) == 1, f"harusnya 1 pasangan, dapat {len(pairs)}"
    p = pairs[0]
    assert p["discharged"]["id"] == "Li2Ti2S4"
    # charged TiS2 telah diskalakan x2:
    assert abs(p["charged"]["V"] - 110.0) < 1e-6, p["charged"]["V"]
    assert abs(p["charged"]["E"] - (-40.0)) < 1e-6, p["charged"]["E"]
    assert p["x2"] == 2 and p["x1"] == 0

    e_metal = {"Li": -1.90}
    props = properties.compute_properties(p, e_metal)
    # V_av = -(E_disch - E_chg - (x2-x1)*E_Li)/(q*(x2-x1))
    #      = -(-46 - (-40) - 2*(-1.9))/(1*2) = -(-46+40+3.8)/2 = -(-2.2)/2 = 1.1
    assert abs(props["V_av"] - 1.10) < 1e-3, props["V_av"]
    assert abs(props["dV_percent"] - 9.0909) < 1e-2, props["dV_percent"]
    print("OK  commensurate scaling Li2Ti2S4/TiS2:",
          f"V_av={props['V_av']} dV%={props['dV_percent']}")


def test_no_false_pair():
    """Material dengan kerangka berbeda TIDAK boleh dipasangkan."""
    materials = [
        {"id": "NbS2", "formula": "NbS2",
         "composition": {"Nb": 1, "S": 2}, "nsites": 3,
         "volume": 60.0, "energy_cell": -20.0,
         "space_group": 160, "crystal_system": "trigonal"},
        {"id": "NaNbO2", "formula": "NaNbO2",
         "composition": {"Na": 1, "Nb": 1, "O": 2}, "nsites": 4,
         "volume": 50.0, "energy_cell": -25.0,
         "space_group": 166, "crystal_system": "trigonal"},
    ]
    pairs = pair_matching.find_pairs(materials, metals=["Na"])
    assert len(pairs) == 0, "S vs O berbeda kerangka, tak boleh dipasangkan"
    print("OK  tidak ada pasangan palsu (kerangka beda)")


def test_negative_voltage():
    """Elektroda voltase negatif harus tetap terhitung (bukan dibuang)."""
    materials = [
        {"id": "LiC12", "formula": "LiC12",
         "composition": {"Li": 1, "C": 12}, "nsites": 13,
         "volume": 200.0, "energy_cell": -120.0,
         "space_group": 194, "crystal_system": "hexagonal"},
        {"id": "LiC6", "formula": "LiC6",
         "composition": {"Li": 2, "C": 12}, "nsites": 14,
         "volume": 205.0, "energy_cell": -122.1,
         "space_group": 194, "crystal_system": "hexagonal"},
    ]
    # Kerangka = C12; Li berbeda (1 vs 2). LiC6 (2 Li) = discharged.
    pairs = pair_matching.find_pairs(materials, metals=["Li"])
    assert len(pairs) == 1
    p = pairs[0]
    assert p["x2"] == 2 and p["x1"] == 1
    e_metal = {"Li": -1.90}
    props = properties.compute_properties(p, e_metal)
    # V_av = -(-122.1 - (-120) - 1*(-1.9))/(1*1) = -(-122.1+120+1.9) = 0.2
    assert abs(props["V_av"] - 0.2) < 1e-3, props["V_av"]
    print("OK  voltase kecil/negatif terhitung:", f"V_av={props['V_av']}")


if __name__ == "__main__":
    test_simple_pair_nbS2_naNbS2()
    test_commensurate_scaling()
    test_no_false_pair()
    test_negative_voltage()
    print("\nSemua test lulus.")
