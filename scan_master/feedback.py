# scan_master/feedback.py
"""
Feedback utilities: convert executed node outcomes into new labels / label updates.

API:
 - apply_node_feedback(node_result, current_labels, current_tick) -> list of new_labels
   node_result: node dict produced by Node Builder, may include 'outcome' and 'success' flags.
   current_labels: list of raw labels (space labels) in that region (so we can set owner, reduce mass, etc.)
"""
from typing import Dict, Any, List
from .utils import mk_label

def _emit_perforin_pulse(executor_id: str, tick: int) -> Dict[str, Any]:
    return mk_label("PERFORIN_PULSE", mass=1.0, created_tick=tick, owner=executor_id, meta={"source":"CTL"})

def _emit_spilled_antigen(mass: float, tick: int) -> Dict[str, Any]:
    return mk_label("SPILLED_ANTIGEN", mass=mass, created_tick=tick, meta={"source":"spill"})

def _emit_dc_presenting(dc_id: str, tick: int) -> Dict[str, Any]:
    return mk_label("DC_PRESENTING", mass=1.0, created_tick=tick, owner=dc_id)

def _emit_owned_antigen(dc_id: str, mass: float, tick: int) -> Dict[str, Any]:
    return mk_label("OWNED_ANTIGEN", mass=mass, created_tick=tick, owner=dc_id)

def apply_node_feedback(node: Dict[str, Any], current_labels: List[Dict[str, Any]], current_tick: int) -> List[Dict[str, Any]]:
    """
    Convert a single node into new/modified labels.
    Very small deterministic rules for demo:
      - node_type == 'Tcell_antigen_contact' and node has positive outcome -> if kill/activation -> produce MHC_PEPTIDE on presenting cell (simulated)
      - node_type == 'Tcell_prime' -> no immediate label but returns IL2 mass if success
      - node_type == 'Antigen_sampling' -> if DC sampled, produce ANTIGEN_HANDOVER + OWNED_ANTIGEN (transfer)
      - node_type == 'Hotspot_manage' -> produce HIGH_DANGER_ZONE event label
      - node_type == 'DC_process_owned_antigen' -> produce MHC_PEPTIDE and DC_PRESENTING
      - node_type == 'Chemotaxis' -> produce nothing (chemo is field already), but we could amplify CXCL10 in region
    """
    out: List[Dict[str, Any]] = []
    ntype = node.get("node_type")
    inputs = node.get("inputs", {})
    success = node.get("outcome", {}).get("success", True)  # default assume success for demo
    executor = node.get("executor", None)  # optional, e.g., DC id or CTL id

    if ntype == "Tcell_antigen_contact" and success:
        # T cell recognition -> we simulate presentation outcome by generating PERFORIN if CTL kill, or IL2 if T cell proliferates
        role = node.get("targets", [])
        # simple: if CTL in targets assume killing -> emit perforin and possibly spill
        if "CTL" in role:
            if executor:
                out.append(_emit_perforin_pulse(executor, current_tick))
            # simulate target cell dying -> produce SPILLED_ANTIGEN
            out.append(_emit_spilled_antigen(mass=2.0, tick=current_tick))
        else:
            # helper signal IL2
            out.append(mk_label("IL2", mass=0.5, created_tick=current_tick))
    elif ntype == "Tcell_prime" and success:
        # prime -> IL2 production small
        out.append(mk_label("IL2", mass=0.3, created_tick=current_tick))
    elif ntype == "Antigen_sampling" and success:
        # DC sampled antigen -> create ANTIGEN_HANDOVER and OWNED_ANTIGEN
        dc_id = executor or "DC_unknown"
        out.append(mk_label("ANTIGEN_HANDOVER", mass=1.0, created_tick=current_tick, owner=dc_id))
        out.append(_emit_owned_antigen(dc_id, mass=1.0, tick=current_tick))
    elif ntype == "DC_process_owned_antigen" and success:
        dc_id = executor or "DC_unknown"
        # produce MHC_PEPTIDE and DC_PRESENTING
        out.append(mk_label("MHC_PEPTIDE", mass=1.0, created_tick=current_tick, owner=dc_id, meta={"epitope":"demo_ep1"}))
        out.append(_emit_dc_presenting(dc_id, current_tick))
    elif ntype == "Hotspot_manage":
        out.append(mk_label("HIGH_DANGER_ZONE", mass=1.0, created_tick=current_tick))
    elif ntype == "Chemotaxis" and success:
        # amplify the chemokine slightly (CXCL10)
        ligand = inputs.get("ligand")
        if ligand == "CXCL10":
            out.append(mk_label("CXCL10", mass=0.5, created_tick=current_tick))
    # default: no output
    return out

