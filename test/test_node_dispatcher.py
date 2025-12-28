from scan_master.cell_master_interface import CellMasterAdapter
# test/test_node_dispatcher.py
# --- mock cell master for test ---
class FakeCellMaster:
    def execute_node(self, node, current_tick=0):
        ntype = node.get("node_type")

        # 1) antigen sampling
        if ntype == "Antigen_sampling":
            return {
                "node_id": node.get("node_id"),
                "node_type": ntype,
                "outcome": {"status": "ok"},
                "emitted_labels": [
                    {"name": "OWNED_ANTIGEN"},
                    {"name": "DC_PRESENTING"},
                ],
                "intents": []
            }

        # 2) T cell antigen contact
        if ntype == "Tcell_antigen_contact":
            return {
                "node_id": node.get("node_id"),
                "node_type": ntype,
                "outcome": {"status": "ok"},
                "emitted_labels": [{"name": "PMHC_SIGNAL"}, {"name": "CTL_ACTIVE"}],
                "intents": [{"action": "activate_Tcell"}]
            }

        # 3) chemotaxis
        if ntype == "Chemotaxis":
            return {
                "node_id": node.get("node_id"),
                "node_type": ntype,
                "outcome": {"status": "ok"},
                "emitted_labels": [],
                "intents": [{"action": "migrate"}]
            }

        # default fallback
        return {
            "node_id": node.get("node_id"),
            "node_type": ntype,
            "outcome": {"status": "failed"},
            "emitted_labels": [],
            "intents": []
        }

# 使用新版 CellMasterAdapter 包起来
cmi = CellMasterAdapter(FakeCellMaster())

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scan_master.node_dispatcher import dispatch_nodes

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def test_dispatch_basic():
    # sample node requests (mimic outputs from node_builder/triggers)
    nodes = [
        {"node_type": "Antigen_sampling", "inputs": {"ligand":"ANTIGEN_PARTICLE"}, "targets": ["DC"], "priority": 2.0},
        {"node_type": "Tcell_antigen_contact", "inputs": {"ligand":"MHC_PEPTIDE"}, "targets": ["NAIVE_T","CTL"], "priority": 3.3},
        {"node_type": "Chemotaxis", "inputs": {"ligand":"CXCL10"}, "targets": ["TH1","CTL"], "priority": 1.5},
    ]
    out = dispatch_nodes(nodes, cmi, current_tick=5)
    # basic shape checks
    expect("results" in out and "emitted_labels" in out and "intents" in out, "dispatch returned expected keys")
    # Antigen_sampling should have produced OWNED_ANTIGEN and DC_PRESENTING
    emitted_names = [l["name"] for l in out["emitted_labels"]]
    expect(any(x in emitted_names for x in ("OWNED_ANTIGEN","ANTIGEN_HANDOVER","DC_PRESENTING")), "Antigen sampling emitted expected labels")
    # T cell node should have produced an activation intent + CTL_ACTIVE
    intent_actions = [i["action"] for i in out["intents"] if "action" in i]
    expect(any(a == "activate_Tcell" for a in intent_actions), "T cell activation intent produced")
    expect(any(l["name"] == "CTL_ACTIVE" for l in out["emitted_labels"]), "CTL_ACTIVE label produced")

def run_all():
    print("Running node_dispatcher tests...")
    test_dispatch_basic()
    print("All node_dispatcher tests passed.")

if __name__ == "__main__":
    run_all()

