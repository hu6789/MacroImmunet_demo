# test/test_triggers.py  (expanded full-version)
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scan_master.space import Space
from scan_master.aggregator import LabelAggregator
from scan_master.triggers import apply_triggers_to_region
from scan_master.utils import mk_label

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def dump_res(res):
    print("== EMITTED ==")
    for e in res.get("emitted", []):
        print(" ", e.get("name"), " mass=", e.get("mass"), " owner=", e.get("owner"), " meta=", e.get("meta"))
    print("== NODE REQUESTS ==")
    for n in res.get("node_requests", []):
        print(" ", n.get("node_type"), " targets=", n.get("targets"), " pri=", n.get("priority"))

def test_hotspot_and_handover_expanded():
    s = Space()
    r = "trig_r"

    # seed region with antigen particles and a DAMP
    s.add_label(r, mk_label("S_RBD", mass=8.0, created_tick=0))
    s.add_label(r, mk_label("S_RBD", mass=4.0, created_tick=1))
    s.add_label(r, mk_label("DAMP_frag", mass=1.0, created_tick=2))

    # also add a DC label so antigen handover can claim owner
    s.add_label(r, mk_label("DC", mass=1.0, created_tick=2, meta={"cell_type":"DC"}))

    agg = LabelAggregator({"young_thresh":3,"recent_spill_window":5})
    ligand_summary = agg.aggregate_labels(s.get_labels(r))
    spectrum = agg.get_spectrum(s.get_labels(r), current_tick=3)
    res = apply_triggers_to_region(s, r, ligand_summary, spectrum, current_tick=3)

    # debug dump (helpful if something fails)
    dump_res(res)

    emitted = res.get("emitted", [])
    names = [e["name"] for e in emitted]

    # Expect HIGH_DANGER_ZONE due to antigen + DAMP
    expect("HIGH_DANGER_ZONE" in names, "HIGH_DANGER_ZONE emitted")

    # Expect ANTIGEN_HANDOVER and OWNED_ANTIGEN and DC_PRESENTING and/or MHC_PEPTIDE
    expect(any(n in names for n in ("ANTIGEN_HANDOVER","OWNED_ANTIGEN","DC_PRESENTING","MHC_PEPTIDE")), "handover/presentation emitted")

    # Node requests should include something meaningful (Antigen_sampling or Tcell nodes)
    nr = res.get("node_requests", [])
    ntypes = [n.get("node_type") for n in nr]
    expect(len(nr) > 0, "some node_requests produced")
    expect(any(nt in ntypes for nt in ("Antigen_sampling","Tcell_antigen_contact","Tcell_prime")), "node requests include antigen or T cell nodes")

    # If OWNED_ANTIGEN emitted, ensure it has an owner set when DC present
    owned = [e for e in emitted if e["name"] == "OWNED_ANTIGEN"]
    if owned:
        expect(any(e.get("owner") is not None for e in owned), "OWNED_ANTIGEN has owner set when DC present")

def test_prr_and_chemotaxis_expanded():
    s = Space()
    r = "trig_r2"
    # seed INFECTED and CXCL10 field
    s.add_label(r, mk_label("INFECTED", mass=1.0, created_tick=0))
    s.add_label(r, mk_label("CXCL10", mass=2.0, created_tick=0))

    agg = LabelAggregator()
    ligand_summary = agg.aggregate_labels(s.get_labels(r))
    spectrum = agg.get_spectrum(s.get_labels(r), current_tick=1)
    res = apply_triggers_to_region(s, r, ligand_summary, spectrum, current_tick=1)

    dump_res(res)

    names = [e["name"] for e in res.get("emitted", [])]

    # PRR activation must be emitted when INFECTED exists
    expect("PRR_ACTIVATED" in names, "PRR activation emitted for INFECTED")

    # Chemokine CXCL10 should be preserved/emitted as a chemo hint (propagated)
    expect("CXCL10" in names, "CXCL10 chemo hint emitted")

    # IFNG / IL12 should be seeded by prr_activation_rule
    expect(any(x in names for x in ("IFNG","IL12")), "IFNG or IL12 seeded on PRR activation")

def test_infection_entry_and_mhc_tcr_path():
    s = Space()
    r = "trig_r3"

    # Setup ACE2 on epithelium, antigen particles, DC and TCR token
    s.add_label(r, mk_label("ACE2_PRESENT", mass=1.0, created_tick=0, meta={"token":"ACE2_PRESENT"}))
    s.add_label(r, mk_label("S_RBD", mass=10.0, created_tick=0))
    s.add_label(r, mk_label("DC", mass=1.0, created_tick=0, meta={"cell_type":"DC"}))
    s.add_label(r, mk_label("TCR_PERTYPE", mass=1.0, created_tick=0, meta={"token":"TCR_PERTYPE"}))

    agg = LabelAggregator()
    ligand_summary = agg.aggregate_labels(s.get_labels(r))
    spectrum = agg.get_spectrum(s.get_labels(r), current_tick=1)
    res = apply_triggers_to_region(s, r, ligand_summary, spectrum, current_tick=1)

    dump_res(res)

    emitted_names = [e["name"] for e in res.get("emitted", [])]
    node_names = [n.get("node_type") for n in res.get("node_requests", [])]

    # Infection path: INFECTED and VIRTUAL replication markers expected
    expect("INFECTED" in emitted_names, "INFECTED emitted for ACE2 + antigen")
    expect("VIRAL_REPLICATING" in emitted_names or "PRR_ACTIVATED" in emitted_names, "viral/PRR pathway engaged")

    # Expect handover/presentation outputs when DC present
    expect(any(n in emitted_names for n in ("ANTIGEN_HANDOVER","OWNED_ANTIGEN","MHC_PEPTIDE","DC_PRESENTING")), "handover/presentation emitted in infection scenario")

    # TCR/MHC pairing should produce Tcell node requests when TCR token present
    expect(any(nt in node_names for nt in ("Tcell_antigen_contact","Tcell_prime")), "T cell node requests present for MHC+TCR")

def run_all():
    print("Running triggers tests...")
    test_hotspot_and_handover_expanded()
    test_prr_and_chemotaxis_expanded()
    test_infection_entry_and_mhc_tcr_path()
    print("All triggers tests passed.")

if __name__ == "__main__":
    run_all()

