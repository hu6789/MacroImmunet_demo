#!/usr/bin/env python3
"""
Minimal Step3 driver for the demo — robustly handles labels that are dicts or objects.
"""
from scan_master.space import Space
from cell_master.masters.antigen_master import AntigenMaster
from cell_master.intent_executor import execute_intents
from scan_master.aggregator import LabelAggregator
from scan_master.node_builder import build_nodes_from_summary
from scan_master.receptor_registry import match_receptors_from_summary
import time

def _label_field(lbl, *keys, default=None):
    """
    Safe accessor: try dict keys then object attrs.
    keys: sequence of alternative names to try, returns first found.
    """
    if lbl is None:
        return default
    for k in keys:
        # try dict
        try:
            if isinstance(lbl, dict) and k in lbl:
                return lbl.get(k)
        except Exception:
            pass
        # try meta subkeys for convenience
        try:
            if isinstance(lbl, dict) and "meta" in lbl and isinstance(lbl["meta"], dict) and k in lbl["meta"]:
                return lbl["meta"].get(k)
        except Exception:
            pass
        # try object attrs
        try:
            if hasattr(lbl, k):
                return getattr(lbl, k)
        except Exception:
            pass
    return default

def pretty_label(lbl):
    """Return (id/name, type, meta) tuple in a robust way for printing."""
    lid = _label_field(lbl, "id", "name")
    ltype = _label_field(lbl, "type", "meta_type", "meta")  # best-effort
    meta = None
    try:
        if isinstance(lbl, dict):
            meta = lbl.get("meta")
        else:
            meta = getattr(lbl, "meta", None)
    except Exception:
        meta = None
    return (lid, ltype, meta)

def run_demo(ticks=6):
    s = Space()
    ant = AntigenMaster(space=s)
    agg = LabelAggregator()

    # spawn one antigen agent like tests do
    aid = ant.spawn_agent(coord=(0,0), proto={'amount':2.0,'epitopes':[{'seq':'PEP_TEST_123','score':1.0}], 'origin':'test_injection','type':'VIRUS'})
    print(f"[demo] spawned agent {aid}")

    for tick in range(1, ticks+1):
        print(f"\n=== TICK {tick} ===")
        ant.step(region_id='epi_1', rng=ant.rng, tick=tick)

        labels = s.get_labels('epi_1') or []
        pretty = [pretty_label(l) for l in labels]
        print("labels (id, type, meta):")
        if pretty:
            for p in pretty:
                print(" -", p)
        else:
            print(" - (none)")

        # aggregator / node building (demo)
        aglist = agg.aggregate_labels(labels)
        print("aggregated ligands:", aglist)
        hits = match_receptors_from_summary(aglist)
        print("receptor hits:", hits)
        nodes = build_nodes_from_summary(aglist, hits)
        print("nodes:", [(n['node_type'], n['targets']) for n in nodes])

        # optional: execute a simple intent if some node exists (demo)
        if nodes:
            # build one simple EMIT_CYTOKINE intent for demo
            intents = []
            for n in nodes:
                if n['node_type'] == 'Chemotaxis':
                    intents.append({'intent_type':'EMIT_CYTOKINE', 'cytokine':'CXCL10', 'amount':1.0, 'coord': n.get('coord')})
            if intents:
                execute_intents(s, region_id='epi_1', intents=intents)
                print("[demo] executed intents:", intents)

        # small sleep so timestamps differ when you run interactively
        time.sleep(0.01)

if __name__ == "__main__":
    run_demo()
