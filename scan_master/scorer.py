# scan_master/scorer.py
"""
Scorer for MacroImmunet_demo

API:
 - score_nodes(spectrum:dict, nodes:list, receptor_hits:list, k:int=5) -> list of scored nodes (desc by score)
 - score_hotspots(spectra:list_of_spectrum_dicts, k:int=5) -> ranked hotspots (based on spectrum features)

Scoring design (simple, transparent):
 - node_score = node.priority * (1 + log(1 + sum_receptor_scores_for_node))
 - receptor_scores taken from receptor_hits.score (mass-based heuristic)
 - we optionally add spectrum bonuses: dominant_mass, young_mass fraction, num_mhc, num_damp
 - final score normalized for ranking
"""

from typing import List, Dict, Any
import math

def _sum_receptor_scores_for_node(node: Dict[str, Any], receptor_hits: List[Dict[str, Any]]) -> float:
    # receptors relevant to node are those whose ligand appears in node.inputs or all if not specified
    lig = node.get("inputs", {}).get("ligand")
    if lig:
        relevant = [h for h in receptor_hits if h.get("ligand") == lig]
    else:
        # fallback: any hit that targets node targets
        targets = set(node.get("targets", []))
        relevant = [h for h in receptor_hits if targets.intersection(set(h.get("target_cell_types", [])))]
    return sum(float(h.get("score", 0.0)) for h in relevant)

def _spectrum_bonus(spectrum: Dict[str, Any]) -> float:
    # simple bonus: favor high dominant mass and recent young_mass
    dom = float(spectrum.get("dominant_mass", 0.0))
    total = float(spectrum.get("total_mass", 1.0))
    young = float(spectrum.get("young_mass", 0.0))
    num_mhc = float(spectrum.get("num_mhc", 0.0))
    num_damp = float(spectrum.get("num_damp", 0.0))
    # normalized features
    dom_frac = dom / (total + 1e-12)
    young_frac = young / (total + 1e-12)
    return dom_frac * 0.8 + young_frac * 0.5 + num_mhc * 0.1 + num_damp * 0.05

def score_nodes(spectrum: Dict[str, Any], nodes: List[Dict[str, Any]], receptor_hits: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
    """
    Returns top-k nodes with attached 'score' field.
    """
    scored = []
    spec_bonus = _spectrum_bonus(spectrum)
    for n in nodes:
        base_priority = float(n.get("priority", 1.0))
        rec_sum = _sum_receptor_scores_for_node(n, receptor_hits)
        # node score formula (transparent)
        node_score = base_priority * (1.0 + math.log1p(rec_sum)) * (1.0 + spec_bonus)
        scored.append({**n, "score": node_score, "receptor_influence": rec_sum, "spectrum_bonus": spec_bonus})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]

def score_hotspots(spectra: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
    """
    Rank region spectra (hotspots) by a simple function:
      hotspot_score = total_mass_weight * total_mass + dominant_mass_weight * dominant_mass + danger_weight*num_damp + young_mass_weight*young_mass
    """
    ranked = []
    for s in spectra:
        total = float(s.get("total_mass", 0.0))
        dom = float(s.get("dominant_mass", 0.0))
        young = float(s.get("young_mass", 0.0))
        num_damp = float(s.get("num_damp", 0.0))
        # weights (tunable)
        score = (1.0 * total) + (0.8 * dom) + (0.6 * young) + (1.2 * num_damp)
        ranked.append({**s, "hotspot_score": score})
    ranked.sort(key=lambda x: x["hotspot_score"], reverse=True)
    return ranked[:k]

# smoke test
if __name__ == "__main__":
    # example spectrum
    spec = {"total_mass": 18.6, "dominant_mass": 15.0, "young_mass": 17.6, "num_mhc": 1, "num_damp": 1}
    nodes = [
        {"node_type":"Tcell_antigen_contact","priority":3.0,"inputs":{"ligand":"MHC_PEPTIDE"},"targets":["NAIVE_T"]},
        {"node_type":"Tcell_prime","priority":2.0,"inputs":{"ligand":"IL12"},"targets":["NAIVE_T"]},
        {"node_type":"Chemotaxis","priority":1.5,"inputs":{"ligand":"CXCL10"},"targets":["TH1","CTL"]}
    ]
    # fake receptor hits
    hits = [
        {"receptor":"TCR","ligand":"MHC_PEPTIDE","score":1.2,"target_cell_types":["NAIVE_T"]},
        {"receptor":"IL12R","ligand":"IL12","score":0.6,"target_cell_types":["NAIVE_T","TH1"]},
        {"receptor":"CXCR3","ligand":"CXCL10","score":2.0,"target_cell_types":["TH1","CTL"]},
    ]
    print("Scored nodes:")
    for n in score_nodes(spec, nodes, hits, k=5):
        print(n["node_type"], "score:", n["score"], "receptor_influence:", n["receptor_influence"])

