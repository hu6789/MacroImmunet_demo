# test/test_decayer.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from scan_master.space import Space
from scan_master.decayer import Decayer

# local mk_label for tests (flexible)
def mk_label(name, mass=1.0, created_tick=0, coord=None, owner=None, meta=None, id=None):
    return {
        "id": id,
        "name": name,
        "mass": mass,
        "created_tick": created_tick,
        "coord": coord,
        "owner": owner,
        "meta": meta or {},
    }

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

# --- helpers for detail checks ---
def find_detail(summary, label_name):
    for d in summary.get("details", []):
        if d.get("name") == label_name:
            return d
    return None

# --- tests ---
def test_decay_many_labels_and_source():
    """
    Test several registry-backed labels: IL12, IL2, IFNG, TNF, SPILLED_ANTIGEN,
    MHC_PEPTIDE, INFECTED, PERFORIN_PULSE. Check masses and hl_source.
    """
    s = Space()
    r = "decay_many"

    # create labels with created_tick = 0 so dt = tick_after
    s.add_label(r, mk_label("IL12", mass=8.0, created_tick=0))
    s.add_label(r, mk_label("IL2", mass=6.0, created_tick=0))
    s.add_label(r, mk_label("IFNG", mass=8.0, created_tick=0))
    s.add_label(r, mk_label("TNF", mass=10.0, created_tick=0))
    s.add_label(r, mk_label("SPILLED_ANTIGEN", mass=100.0, created_tick=0))
    s.add_label(r, mk_label("MHC_PEPTIDE", mass=12.0, created_tick=0))
    s.add_label(r, mk_label("INFECTED", mass=5.0, created_tick=0))
    s.add_label(r, mk_label("PERFORIN_PULSE", mass=0.5, created_tick=0))

    d = Decayer(removal_threshold=1e-9)
    tick_after = 8
    summary = d.apply_to_region(s, r, current_tick=tick_after)

    # spot-check expected decay using half-life from registry:
    # IL12 half_life=8 -> mass 8 -> 4 after 8 ticks
    il12_detail = find_detail(summary, "IL12")
    expect(il12_detail is not None, "IL12 detail present")
    expect(abs(il12_detail["new_mass"] - 4.0) < 1e-6, f"IL12 decayed to ~4.0 (got {il12_detail['new_mass']})")
    expect(il12_detail["hl_source"].startswith("decayer"), "IL12 used decayer registry or global (hl_source)")

    # IL2 half_life=6 -> after 8 ticks mass = 6 * 0.5**(8/6)
    il2_detail = find_detail(summary, "IL2")
    expect(il2_detail is not None, "IL2 detail present")
    expected_il2 = 6.0 * (0.5 ** (tick_after / 6.0))
    expect(abs(il2_detail["new_mass"] - expected_il2) < 1e-9, "IL2 decayed according to half-life 6")

    # IFNG half_life=8 -> after 8 ticks halves
    ifng_detail = find_detail(summary, "IFNG")
    expect(ifng_detail is not None and abs(ifng_detail["new_mass"] - 4.0) < 1e-6, "IFNG halved after 8 ticks")

    # TNF half_life=10 -> after 8 ticks decays but not halved
    tnf_detail = find_detail(summary, "TNF")
    expect(tnf_detail is not None and tnf_detail["new_mass"] < 10.0 and tnf_detail["new_mass"] > 4.0, "TNF decayed moderately")

    # SPILLED_ANTIGEN half_life=40 -> after 8 ticks small decay factor
    sp_detail = find_detail(summary, "SPILLED_ANTIGEN")
    expect(sp_detail is not None and sp_detail["new_mass"] < 100.0 and sp_detail["new_mass"] > 50.0, "SPILLED_ANTIGEN decayed lightly")

    # MHC_PEPTIDE half_life=12 -> after 8 ticks decayed but still high
    mhc_detail = find_detail(summary, "MHC_PEPTIDE")
    expect(mhc_detail is not None and mhc_detail["new_mass"] < 12.0 and mhc_detail["new_mass"] > 6.0, "MHC_PEPTIDE decayed")

    # INFECTED half_life=10 -> after 8 ticks still present
    infected_detail = find_detail(summary, "INFECTED")
    expect(infected_detail is not None and infected_detail["new_mass"] > 0.0, "INFECTED present after 8 ticks")

    # PERFORIN_PULSE half_life=1 -> after 8 ticks should have decayed heavily
    perf_detail = find_detail(summary, "PERFORIN_PULSE")
    expect(perf_detail is not None and perf_detail["new_mass"] < 1e-2, "PERFORIN_PULSE decayed heavily after 8 ticks")

def test_removal_and_threshold_behavior():
    """
    Test label removal when mass decays below removal_threshold.
    Also test that unknown labels without half_life are kept if no global default.
    """
    s = Space()
    r = "decay_remove"
    # short half-life label
    s.add_label(r, mk_label("PERFORIN_PULSE", mass=0.5, created_tick=0))
    # unknown label (no half-life in registry) should remain if no global default
    s.add_label(r, mk_label("UNKNOWN_KEEP", mass=2.0, created_tick=0))

    d = Decayer(removal_threshold=1e-4)
    # apply long time so perforin goes near zero and should be removed
    summary = d.apply_to_region(s, r, current_tick=200)
    # PERFORIN removed
    perfin = find_detail(summary, "PERFORIN_PULSE")
    expect(perfin is not None and perfin["new_mass"] <= d.removal_threshold, "PERFORIN decayed below threshold")
    # Unknown label: since no global_default set, it is non-decaying and should still be present in space
    remaining = s.get_labels(r)
    names = [l["name"] for l in remaining]
    expect("UNKNOWN_KEEP" in names, "UNKNOWN_KEEP preserved (no global default)")

def test_set_half_life_and_global_default():
    """
    Test set_half_life override and global_default_half_life fallback behavior.
    """
    s = Space()
    r = "decay_override"
    s.add_label(r, mk_label("CUSTOM_LABEL", mass=10.0, created_tick=0))
    # create decayer with a global default -> causes CUSTOM_LABEL to decay
    d = Decayer(removal_threshold=1e-9, global_default_half_life=5.0)
    summary1 = d.apply_to_region(s, r, current_tick=5)
    det1 = find_detail(summary1, "CUSTOM_LABEL")
    expect(det1 is not None and abs(det1["new_mass"] - 5.0) < 1e-6, "custom label decayed by global default (half)")

    # override a registry label
    s2 = Space()
    s2.add_label(r, mk_label("IL12", mass=8.0, created_tick=0))
    d2 = Decayer(removal_threshold=1e-9)
    # override IL12 to half_life=16
    d2.set_half_life("IL12", 16.0)
    summary2 = d2.apply_to_region(s2, r, current_tick=8)
    det2 = find_detail(summary2, "IL12")
    # now 8 ticks with half-life 16 -> mass = 8 * 0.5**(8/16) = 8 * 0.5**0.5 ~ 8 * 0.7071 = 5.656854
    expect(det2 is not None and abs(det2["new_mass"] - (8.0 * (0.5 ** (8.0/16.0)))) < 1e-9, "set_half_life override effective")
    expect(det2["hl_source"] == "decayer_registry", "override visible via decayer_registry")

def run_all():
    print("Running decayer tests...")
    test_decay_many_labels_and_source()
    test_removal_and_threshold_behavior()
    test_set_half_life_and_global_default()
    print("All decayer tests passed.")

if __name__ == "__main__":
    run_all()

