# Step4_minidriver.py — minimal T cell activation demo for Step4
# Drop into project root and run:
# PYTHONPATH=. python3 Step4_minidriver.py

import time
from scan_master.space import Space
from cell_master.masters.antigen_master import AntigenMaster
from scan_master.aggregator import LabelAggregator
from scan_master.node_builder import build_nodes_from_summary
from scan_master.receptor_registry import match_receptors_from_summary
from cell_master.behavior_mapper import map_node_to_intents
from cell_master.intent_executor import execute_intents

# --- helper utils for the demo ---
def ensure_naive_t_in_space(space, region_id='epi_1'):
    """Ensure there is at least one NAIVE_T label for activation to target."""
    labs = space.get_labels(region_id)
    # look for any NAIVE_T
    for l in labs:
        meta = l.get('meta', {})
        if meta.get('type') == 'NAIVE_T' or l.get('meta', {}).get('canonical') == 'NAIVE_T':
            return
    # else append a minimal NAIVE_T label (positioned at origin)
    nt = {
        "id": "t_naive_1",
        "coord": (0.0, 0.0),
        "meta": {"type": "NAIVE_T", "state": "resting", "created_tick": int(time.time())},
    }
    # try common insertion paths
    try:
        if hasattr(space, "add_label"):
            # some space.add_label take (region, label) or (label,)
            try:
                space.add_label(region_id, nt)
            except Exception:
                try:
                    space.add_label(nt)
                except Exception:
                    # fallback to _local_labels / labels
                    raise
        elif hasattr(space, "_local_labels"):
            ll = getattr(space, "_local_labels")
            if isinstance(ll, dict):
                ll.setdefault(region_id, []).append(nt)
            elif isinstance(ll, list):
                ll.append(nt)
        elif hasattr(space, "labels") and isinstance(getattr(space, "labels"), list):
            space.labels.append(nt)
    except Exception:
        # last resort: attach labels attribute
        if not hasattr(space, "labels") or space.labels is None:
            space.labels = []
        space.labels.append(nt)

def find_mhc_peptides(labels):
    """Return list of MHC_PEPTIDE labels found in label list"""
    out = []
    for l in labels:
        meta = l.get('meta', {})
        if meta.get('type') == 'MHC_PEPTIDE' or l.get('meta', {}).get('type') == 'MHC_PEPTIDE':
            out.append(l)
    return out

def activate_naive_t(space, region_id, mhc_label):
    """Simulate naive T activation upon seeing a pMHC: writes activation label(s)."""
    epitope = mhc_label.get('meta', {}).get('epitope') or mhc_label.get('meta', {}).get('epitopes') or mhc_label.get('meta', {}).get('epitope', {'seq':'UNKNOWN'})
    # canonicalize epitope seq if nested list/dict
    seq = None
    if isinstance(epitope, dict):
        seq = epitope.get('seq')
    elif isinstance(epitope, list) and len(epitope) > 0 and isinstance(epitope[0], dict):
        seq = epitope[0].get('seq')
    else:
        seq = str(epitope)

    # create an activation label
    act_id = f"t_activation_{mhc_label.get('id')}_{int(time.time())}"
    act_lab = {
        "id": act_id,
        "coord": (0.0, 0.0),
        "meta": {
            "type": "T_CELL_ACTIVATION",
            "epitope": {"seq": seq},
            "info": {"source_mhc": mhc_label.get('id')},
            "created_tick": int(time.time()),
        }
    }

    try:
        # try space.add_label variants
        if hasattr(space, "add_label"):
            try:
                space.add_label(region_id, act_lab)
            except Exception:
                try:
                    space.add_label(act_lab)
                except Exception:
                    raise
        elif hasattr(space, "_local_labels"):
            ll = getattr(space, "_local_labels")
            if isinstance(ll, dict):
                ll.setdefault(region_id, []).append(act_lab)
            elif isinstance(ll, list):
                ll.append(act_lab)
        elif hasattr(space, "labels") and isinstance(getattr(space, "labels"), list):
            space.labels.append(act_lab)
    except Exception:
        # fallback: attach to space.labels
        if not hasattr(space, "labels") or space.labels is None:
            space.labels = []
        space.labels.append(act_lab)

    # also mark a CTL / TH1 label as a simple demonstration
    ctl_lab = {
        "id": f"ctl_active_{seq}_{int(time.time())}",
        "coord": (0.0, 0.0),
        "meta": {"type": "CTL_ACTIVE", "epitope": {"seq": seq}, "created_tick": int(time.time())}
    }
    try:
        if hasattr(space, "add_label"):
            try:
                space.add_label(region_id, ctl_lab)
            except Exception:
                try:
                    space.add_label(ctl_lab)
                except Exception:
                    raise
        elif hasattr(space, "_local_labels"):
            ll = getattr(space, "_local_labels")
            if isinstance(ll, dict):
                ll.setdefault(region_id, []).append(ctl_lab)
            elif isinstance(ll, list):
                ll.append(ctl_lab)
        elif hasattr(space, "labels") and isinstance(getattr(space, "labels"), list):
            space.labels.append(ctl_lab)
    except Exception:
        if not hasattr(space, "labels") or space.labels is None:
            space.labels = []
        space.labels.append(ctl_lab)

    return {"activated_label": act_lab, "ctl_label": ctl_lab}

# --- demo runtime ---
def run_step4_demo():
    region = 'epi_1'
    s = Space()
    ant = AntigenMaster(space=s)
    agg = LabelAggregator()

    # spawn antigen and step once to produce MHC via existing pipeline (as you did previously)
    aid = ant.spawn_agent(coord=(0,0), proto={'amount':2.0,'epitopes':[{'seq':'PEP_TEST_123','score':1.0}], 'origin':'test_injection','type':'VIRUS'})
    ant.step(region_id=region, rng=ant.rng, tick=1)

    # ensure a naive T exists
    ensure_naive_t_in_space(s, region)

    # collect labels and find MHCs
    labels = s.get_labels(region)
    mhcs = find_mhc_peptides(labels)
    print("FOUND MHC_PEPTIDE labels:", [m.get('id') for m in mhcs])

    if not mhcs:
        print("No MHC present — run antigen pipeline (ant.step + executor) first.")
        return

    # for each MHC, simulate naive T activation
    events = []
    for mh in mhcs:
        ev = activate_naive_t(s, region, mh)
        events.append(ev)
        print("Activated on epitope:", ev['activated_label']['meta'].get('epitope'))

    print("\nSPACE LABELS AFTER ACTIVATION (summary):")
    labs = s.get_labels(region)
    for l in labs:
        print(" -", l.get('id'), "type:", l.get('meta', {}).get('type'))

if __name__ == "__main__":
    run_step4_demo()

