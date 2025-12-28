# scan_master/node_builder.py
"""
Node builder: transform ligand_summary + receptor_hits -> node candidates.

Provides:
 - build_nodes_from_summary(ligand_summary, receptor_hits)
 - build_nodes_from_space(space, region_id, aggregator=None, radius=1, tick=None)

Node schema:
{
  'node_id': str,
  'node_type': str,
  'coord': optional coord,
  'inputs': {...},
  'targets': [...],
  'priority': float
}
"""
from typing import List, Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

def _make_node(node_type: str, inputs: Dict[str, Any], targets: List[str], priority: float=1.0, coord: Any=None) -> Dict[str, Any]:
    return {
        "node_id": f"{node_type}_{uuid.uuid4().hex[:8]}",
        "node_type": node_type,
        "coord": coord,
        "inputs": inputs,
        "targets": targets,
        "priority": float(priority)
    }


def build_nodes_from_summary(ligand_summary: List[Dict[str, Any]], receptor_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construct nodes from ligand_summary + receptor_hits.

    Rules (simple demo):
     - IL12 + IL12R -> Tcell_prime targeting NAIVE_T, TH1
     - MHC_PEPTIDE + TCR -> Tcell_antigen_contact -> NAIVE_T, CTL
     - CXCL10 + CXCR3 -> Chemotaxis -> TH1, CTL
     - CCL21 + CCR7 -> DC_migration -> DC
     - ANTIGEN_PARTICLE -> Antigen_sampling -> DC
     - PAMP/VIRAL -> DC_alert, Epithelial_alert
    """
    nodes: List[Dict[str, Any]] = []
    lig_map = {l.get("ligand"): l for l in (ligand_summary or [])}
    # helper: hits for canonical ligand names
    def hits_for_lig(lig: str):
        return [h for h in (receptor_hits or []) if h.get("ligand") == lig]

    # IL12 -> prime
    if "IL12" in lig_map and hits_for_lig("IL12"):
        nodes.append(_make_node("Tcell_prime", {"ligand": "IL12", "mass": lig_map["IL12"].get("mass", 0.0)}, targets=["NAIVE_T", "TH1"], priority=2.0))

    # MHC -> antigen contact
    if "MHC_PEPTIDE" in lig_map and hits_for_lig("MHC_PEPTIDE"):
        nodes.append(_make_node("Tcell_antigen_contact", {"ligand": "MHC_PEPTIDE", "mass": lig_map["MHC_PEPTIDE"].get("mass", 0.0)}, targets=["NAIVE_T", "CTL"], priority=3.0))

    # Chemokine CXCL10 -> chemotaxis
    if "CXCL10" in lig_map and hits_for_lig("CXCL10"):
        nodes.append(_make_node("Chemotaxis", {"ligand": "CXCL10", "mass": lig_map["CXCL10"].get("mass", 0.0)}, targets=["TH1", "CTL"], priority=1.5))

    # CCL21 -> DC migration
    if "CCL21" in lig_map and hits_for_lig("CCL21"):
        nodes.append(_make_node("DC_migration", {"ligand": "CCL21", "mass": lig_map["CCL21"].get("mass", 0.0)}, targets=["DC"], priority=1.5))

    # PAMP/PRR -> alerts
    if "VIRAL_REPLICATING" in lig_map or "PAMP_FRAG" in lig_map:
        nodes.append(_make_node("DC_alert", {"reason": "PRR/PAMP"}, targets=["DC"], priority=3.0))
        nodes.append(_make_node("Epithelial_alert", {"reason": "PRR/PAMP"}, targets=["EPITHELIAL"], priority=2.0))

    # Owned antigen -> process
    if "OWNED_ANTIGEN" in lig_map:
        nodes.append(_make_node("DC_process_owned_antigen", {"ligand": "OWNED_ANTIGEN", "mass": lig_map["OWNED_ANTIGEN"].get("mass", 0.0)}, targets=["DC"], priority=2.5))

    # ANTIGEN_PARTICLE -> antigen sampling
    if "ANTIGEN_PARTICLE" in lig_map:
        nodes.append(_make_node("Antigen_sampling", {"ligand": "ANTIGEN_PARTICLE", "mass": lig_map["ANTIGEN_PARTICLE"].get("mass", 0.0)}, targets=["DC"], priority=1.2))

    # HIGH_DANGER_ZONE -> manage
    if "HIGH_DANGER_ZONE" in lig_map:
        nodes.append(_make_node("Hotspot_manage", {"ligand": "HIGH_DANGER_ZONE"}, targets=["DC", "TH1", "CTL"], priority=3.5))

    # attach receptor_hits subset to each node (defensive)
    for n in nodes:
        lig = n["inputs"].get("ligand")
        if lig:
            n["inputs"]["receptor_hits"] = [h for h in (receptor_hits or []) if h.get("ligand") == lig]
        else:
            n["inputs"]["receptor_hits"] = list(receptor_hits or [])

    # sort by priority desc
    nodes.sort(key=lambda x: x.get("priority", 0.0), reverse=True)
    return nodes


# ---- convenience: build nodes directly from a space + region (uses aggregator if provided) ----
def build_nodes_from_space(space: Any, region_id: str, aggregator: Optional[Any] = None, radius: int = 1, tick: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Wrap: (space -> aggregated ligand_summary) + receptor_hits -> nodes
    aggregator: object with aggregate_region(space, region_id) and/or get_default_aggregator
    """
    # lazy import to avoid cycles in some setups
    try:
        from .receptor_registry import match_receptors_from_summary
    except Exception:
        # try relative import fallback
        from scan_master.receptor_registry import match_receptors_from_summary

    # get ligand summary
    ls = None
    if aggregator and hasattr(aggregator, "aggregate_region"):
        try:
            ls = aggregator.aggregate_region(space, region_id, radius=radius)
        except Exception:
            ls = None

    if ls is None:
        # fallback to trying to read labels from space
        try:
            if hasattr(space, "get_labels"):
                raw = space.get_labels(region_id)
            elif hasattr(space, "list_labels"):
                raw = space.list_labels(region_id)
            elif hasattr(space, "_local_labels"):
                ll = getattr(space, "_local_labels")
                raw = ll.get(region_id, []) if isinstance(ll, dict) else list(ll)
            else:
                raw = []
        except Exception:
            raw = []
        # try to import aggregator locally if available
        try:
            from .aggregator import LabelAggregator
            local_agg = LabelAggregator()
            ls = local_agg.aggregate_labels(raw, radius=radius)
        except Exception:
            # best-effort convert: count by type
            tmp = {}
            for r in (raw or []):
                key = (r.get("type") or r.get("name") or r.get("id") or "UNKNOWN")
                tmp.setdefault(key, {"ligand": key, "mass": 0.0, "freq": 0})
                tmp[key]["mass"] += float(r.get("mass", 1.0)) if isinstance(r, dict) else 0.0
                tmp[key]["freq"] += 1
            ls = list(tmp.values())

    # match receptors
    hits = []
    try:
        hits = match_receptors_from_summary(ls)
    except Exception as e:
        logger.exception("match_receptors_from_summary failed: %s", e)
        hits = []

    # build nodes from summary + hits
    return build_nodes_from_summary(ls, hits)


# quick smoke when run directly
if __name__ == "__main__":
    sample_ls = [
        {"ligand": "IL12", "mass": 0.6, "freq": 1},
        {"ligand": "CXCL10", "mass": 3.0, "freq": 2},
        {"ligand": "ANTIGEN_PARTICLE", "mass": 8.0, "freq": 1},
        {"ligand": "MHC_PEPTIDE", "mass": 1.0, "freq": 1},
    ]
    # minimal fake receptor hits (would be produced by receptor_registry)
    from scan_master.receptor_registry import match_receptors_from_summary
    hits = match_receptors_from_summary(sample_ls)
    nodes = build_nodes_from_summary(sample_ls, hits)
    for n in nodes:
        print(n["node_type"], "->", n["targets"], "priority", n["priority"])

