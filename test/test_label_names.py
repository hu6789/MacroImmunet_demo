# test/test_label_names.py
# Simple unit tests for scan_master/label_names.py (no pytest required)

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import scan_master.label_names as ln

def expect_msg(ok, msg):
    if ok:
        print("[OK] " + msg)
    else:
        print("[FAIL] " + msg)
        raise AssertionError(msg)

def test_registry_contains_core_labels():
    core = ["EPITHELIAL", "DC", "NAIVE_T", "TH1", "CTL",
            "ANTIGEN_PARTICLE", "ANTIGEN_FIELD", "VIRUS",
            "IL12", "IL2", "IFNG", "CCL21", "CXCL10"]
    for k in core:
        expect_msg(k in ln.LABEL_REGISTRY, f"registry contains {k}")

def test_surface_and_event_lists():
    # surface should include MHC_PEPTIDE, TCR_PERTYPE, ACE2_PRESENT
    for s in ["MHC_PEPTIDE", "TCR_PERTYPE", "ACE2_PRESENT"]:
        expect_msg(s in ln.SURFACE_LABELS, f"{s} in SURFACE_LABELS")
    # events should include INFECTED, PRR_ACTIVATED, HIGH_DANGER_ZONE
    for e in ["INFECTED", "PRR_ACTIVATED", "HIGH_DANGER_ZONE"]:
        expect_msg(e in ln.EVENT_LABELS, f"{e} in EVENT_LABELS")

def test_classify_examples():
    examples = [
        ({"name":"S_RBD","mass":1.0}, "ANTIGEN_PARTICLE"),
        ({"name":"virus_particle","mass":1.0}, "ANTIGEN_PARTICLE"),
        ({"name":"mhc_i_pep","mass":1.0}, "MHC_I"),
        ({"name":"IL-12","mass":0.5}, "IL12"),
        ({"name":"cxcl10","mass":0.2}, "CXCL10"),
        ({"name":"perforin","mass":0.1}, "PERFORIN_PULSE" if "PERFORIN_PULSE" in ln.LABEL_REGISTRY else "DEBRIS"),
    ]
    for raw, expected in examples:
        c = ln.classify_label_item(raw)
        expect_msg(c["canonical"] == expected, f"classify {raw['name']} -> {expected}, got {c['canonical']}")

def test_can_produce_label_behaviour():
    # if label restricts allowed_sources, check allowed / disallowed
    # choose one that we expect to be restricted
    meta = ln.get_label_meta("IL12")
    if meta and meta.get("allowed_sources"):
        # IL12.allowed_sources usually includes DC
        expect_msg(ln.can_produce_label("DC", "IL12"), "DC can produce IL12")
    # label with no allowed_sources should be allowed for any type
    expect_msg(ln.can_produce_label("EPITHELIAL", "ANTIGEN_PARTICLE"), "EPITHELIAL can produce ANTIGEN_PARTICLE (no restriction)")

def test_pretty_classification_no_error():
    s = ln.pretty_classification({"name":"unknown_stuff","mass":0.2})
    expect_msg(isinstance(s, str) and "->" in s, "pretty_classification returns readable string")

def run_all():
    print("Running label_names tests...")
    test_registry_contains_core_labels()
    test_surface_and_event_lists()
    test_classify_examples()
    test_can_produce_label_behaviour()
    test_pretty_classification_no_error()
    print("All label_names tests passed.")

if __name__ == "__main__":
    run_all()

