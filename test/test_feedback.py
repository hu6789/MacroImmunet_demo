# test/test_feedback.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from scan_master.feedback import apply_node_feedback
from scan_master.utils import mk_label

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def test_perforin_spill():
    node = {"node_type":"Tcell_antigen_contact", "targets":["CTL"], "executor":"CTL_1", "outcome":{"success":True}}
    out = apply_node_feedback(node, [], current_tick=10)
    names = [o["name"] for o in out]
    expect("PERFORIN_PULSE" in names, "PERFORIN emitted")
    expect("SPILLED_ANTIGEN" in names, "SPILLED antigen produced")

def test_dc_handover_and_owned():
    node = {"node_type":"Antigen_sampling", "executor":"DC_9", "outcome":{"success":True}}
    out = apply_node_feedback(node, [], current_tick=5)
    names = [o["name"] for o in out]
    expect("ANTIGEN_HANDOVER" in names, "ANTIGEN_HANDOVER emitted")
    expect("OWNED_ANTIGEN" in names, "OWNED_ANTIGEN present")
    # check owner set on owned antigen
    owned = [o for o in out if o["name"] == "OWNED_ANTIGEN"][0]
    expect(owned.get("owner") == "DC_9", "OWNED_ANTIGEN owner set")

def test_dc_process_produces_mhc_presenting():
    node = {"node_type":"DC_process_owned_antigen", "executor":"DC_3", "outcome":{"success":True}}
    out = apply_node_feedback(node, [], current_tick=12)
    names = [o["name"] for o in out]
    expect("MHC_PEPTIDE" in names, "MHC_PEPTIDE produced")
    expect("DC_PRESENTING" in names, "DC_PRESENTING produced")

def run_all():
    print("Running feedback tests...")
    test_perforin_spill()
    test_dc_handover_and_owned()
    test_dc_process_produces_mhc_presenting()
    print("All feedback tests passed.")

if __name__ == "__main__":
    run_all()

