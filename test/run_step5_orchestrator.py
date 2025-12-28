# run_step5_orchestrator.py
"""
Minimal Step5 orchestrator for MacroImmunet_demo (adapted to use a CellMasterAdapter
and a small concrete MyCellMaster that implements execute_node()).

Flow:
 - spawn initial antigen (demo)
 - call AntigenMaster.step(region_id)
 - read space labels, run aggregator -> receptor matching -> node building
 - dispatch nodes to a Master (wrapped by CellMasterAdapter)
 - collect emitted_labels and intents from dispatch, write emitted_labels into Space
 - execute intents (intent_executor) to produce pMHC / debris / etc
 - optional: run tcell activation (if MHC exist)
"""
import time
from typing import List, Dict, Any

from scan_master.space import Space
from cell_master.masters.antigen_master import AntigenMaster
from scan_master.aggregator import LabelAggregator
from scan_master.receptor_registry import match_receptors_from_summary
from scan_master.node_builder import build_nodes_from_summary
from cell_master.behavior_mapper import map_node_to_intents
from cell_master.intent_executor import execute_intents
from cell_master.tcell_activation import activate_tcells
from scan_master.node_dispatcher import dispatch_nodes
from scan_master.cell_master_interface import CellMasterAdapter

# -----------------------
# Small concrete cell-master for orchestrator/demo
# -----------------------
class MyCellMaster:
    """
    Minimal demo CellMaster that implements execute_node(node, current_tick).
    Responsibilities:
      - produce intents for a node using existing behavior_mapper (map_node_to_intents)
      - for some node types (e.g. Antigen_sampling) also "emit" synthetic labels
        (these will be returned in 'emitted_labels' for the dispatcher to apply to space)
    This is intentionally conservative: it DOES NOT mutate Space directly; it returns
    emitted_labels and intents for the caller to apply.
    """
    def __init__(self, node_intent_mapper=None):
        # allow injection (main code uses map_node_to_intents)
        self.node_intent_mapper = node_intent_mapper or map_node_to_intents

    def execute_node(self, node: Dict[str, Any], current_tick: int = 0) -> Dict[str, Any]:
        node_type = node.get("node_type", "")
        node_inputs = node.get("inputs", {})
        emitted: List[Dict[str, Any]] = []
        intents: List[Dict[str, Any]] = []

        # 1) map node -> intents
        try:
            intents = list(self.node_intent_mapper(node) or [])
        except Exception as e:
            # mapping failed => return failed outcome
            return {
                "node_id": node.get("node_id"),
                "node_type": node_type,
                "outcome": {"status": "failed", "error": f"map_node_to_intents_failed: {e}"},
                "emitted_labels": [],
                "intents": []
            }

        # 2) produce demo emitted labels for certain node types
        #    (we keep them minimal and consistent with other demo code)
        if node_type and node_type.lower().startswith("antigen_sampling"):
            # produce an OWNED_ANTIGEN label and a sample MHC_PEPTIDE for DC presenting
            emitted.append({
                "id": f"owned_ant_{current_tick}",
                "name": "OWNED_ANTIGEN",
                "type": "ANTIGEN_PARTICLE",
                "mass": float(node_inputs.get("mass", 1.0)),
                "coord": node.get("coord", None),
                "created_tick": current_tick,
                "meta": {"origin_node": node.get("node_id"), "source": "Antigen_sampling_demo"}
            })
            # produced pMHC summary label (note: executor may also create MHC after intent exec)
            emitted.append({
                "id": f"mhc_sample_{current_tick}",
                "name": "MHC_PEPTIDE",
                "type": "MHC_PEPTIDE",
                "mass": 1.0,
                "coord": node.get("coord", None),
                "created_tick": current_tick,
                "meta": {"origin_node": node.get("node_id")}
            })

        # return normalized result
        return {
            "node_id": node.get("node_id"),
            "node_type": node_type,
            "outcome": {"status": "ok"},
            "emitted_labels": emitted,
            "intents": intents
        }

# ---- orchestrator parameters ----
TICKS = 6
REGION = "epi_1"

def orchestrate_demo(ticks=TICKS):
    # create demo space and masters
    s = Space()
    ant = AntigenMaster(space=s)
    agg = LabelAggregator()

    # create our cell master + adapter and pass to dispatch_nodes
    cm_inst = MyCellMaster()                 # concrete cell master used by dispatcher
    adapter = CellMasterAdapter(cm_inst)     # adapter wraps execute_node semantics if needed

    print("[orchestrator] spawning demo antigen")
    aid = ant.spawn_agent(coord=(0,0),
                          proto={'amount':2.0,'epitopes':[{'seq':'PEP_STEP5','score':1.0}],
                                 'origin':'step5_demo','type':'VIRUS'})
    print("  agent id:", aid)

    for tick in range(1, ticks+1):
        print("\n=== TICK", tick, "===")
        # 1) AntigenMaster step (move & write labels)
        ant.step(region_id=REGION, rng=ant.rng, tick=tick)

        # 2) read labels in space & aggregate
        labels = s.get_labels(REGION)
        print(f"[step] labels in region ({len(labels)}): {[l.get('id') for l in labels]}")
        aglist = agg.aggregate_labels(labels)
        print("[aggregate] aggregated ligands:", aglist)

        # 3) receptor matching
        hits = match_receptors_from_summary(aglist)
        print("[receptors] receptor hits:", hits)

        # 4) node building
        nodes = build_nodes_from_summary(aglist, hits)
        print("[nodes] nodes built:", [(n.get('node_type'), n.get('targets')) for n in nodes])

        # 5) dispatch nodes to cell master via adapter
        if nodes:
            dispatch_out = dispatch_nodes(nodes, adapter, current_tick=tick)
        else:
            dispatch_out = {"results": [], "emitted_labels": [], "intents": []}

        # 6) apply emitted labels to space (dispatcher doesn't mutate space)
        emitted_labels = dispatch_out.get("emitted_labels", [])
        if emitted_labels:
            # use extend_labels so ids are assigned/kept
            s.extend_labels(REGION, emitted_labels)
            print("[dispatch] emitted_labels written to space:", [l.get("name") for l in emitted_labels])
        else:
            print("[dispatch] no emitted_labels")

        # 7) collect intents (from dispatch) and execute them on space
        intents = dispatch_out.get("intents", [])
        if intents:
            print("[intents] executing:", intents)
            evs = execute_intents(s, region_id=REGION, intents=intents)
            print("[execute] executor events:", evs)
        else:
            print("[intents] none produced this tick")

        # 8) activation: let T cells respond if MHC exist
        t_events = activate_tcells(s, REGION, rng=ant.rng, params={"recognition_prob":0.8, "il12_thresh":0.5})
        if t_events:
            print("[activate] tcell activation events:", t_events)
        else:
            print("[activate] no activation this tick")

        time.sleep(0.05)

    # final summary
    final = s.get_labels(REGION)
    print("\n[final] labels in region (summary):")
    for l in final:
        print(" -", l.get("id"), l.get("meta", {}).get("type"), l.get("name"))

if __name__ == "__main__":
    orchestrate_demo()

