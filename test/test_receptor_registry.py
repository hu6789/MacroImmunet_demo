# scan_master/receptor_registry.py
# Minimal receptor registry + matching helper for MacroImmunet_demo

from typing import List, Dict, Any
from .label_names import classify_label_item

# map canonical ligand -> list of receptor descriptors
RECEPTOR_MAP: Dict[str, List[Dict[str, Any]]] = {
    # chemokine -> receptor
    "CXCL10": [
        {"receptor": "CXCR3", "target_cell_types": ["TH1", "CTL"], "score_factor": 1.0}
    ],
    # cytokine -> receptor
    "IL12": [
        {"receptor": "IL12R", "target_cell_types": ["NAIVE_T", "TH1"], "score_factor": 1.0}
    ],
    "IL2": [
        {"receptor": "IL2R", "target_cell_types": ["NAIVE_T", "TH1", "CTL"], "score_factor": 1.0}
    ],
    "IFNG": [
        {"receptor": "IFNGR", "target_cell_types": ["CTL", "DC", "MACROPHAGE"], "score_factor": 1.0}
    ],

    # antigen / entry receptor (important: this is why your test failed before)
    "ANTIGEN_PARTICLE": [
        {"receptor": "ACE2", "target_cell_types": ["EPITHELIAL"], "score_factor": 1.0}
    ],
    # MHC peptide presentation -> TCR
    "MHC_PEPTIDE": [
        {"receptor": "TCR", "target_cell_types": ["NAIVE_T", "TH1", "CTL"], "score_factor": 1.0}
    ],
    # some event hints can be interpreted as receptors/hits if needed
    "INFECTED": [
        {"receptor": "PRR", "target_cell_types": ["DC", "EPITHELIAL"], "score_factor": 0.8}
    ],
}

def normalize_to_canonical(ligand_name: str) -> str:
    """Return canonical label for a ligand name (use label_names heuristics)."""
    if ligand_name is None:
        return None
    # if already canonical and in map, return it
    lname = str(ligand_name).upper()
    if lname in RECEPTOR_MAP:
        return lname
    # otherwise try classify_label_item to map common names like 'S_RBD' -> 'ANTIGEN_PARTICLE'
    try:
        c = classify_label_item({"name": ligand_name})
        return c.get("canonical")
    except Exception:
        return lname

def match_receptors_from_summary(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input: ligand_summary like [{'ligand': 'S_RBD' or 'ANTIGEN_PARTICLE', 'mass':..., 'freq':...}, ...]
    Output: list of receptor hit dicts:
      { 'receptor', 'ligand', 'mass', 'freq', 'score', 'target_cell_types', ... }
    """
    hits: List[Dict[str, Any]] = []
    for l in ligand_summary:
        raw_name = l.get("ligand") or l.get("name")
        canonical = normalize_to_canonical(raw_name)
        if not canonical:
            continue
        descriptors = RECEPTOR_MAP.get(canonical)
        if not descriptors:
            continue
        mass = float(l.get("mass", 0.0))
        freq = int(l.get("freq", 1))
        for desc in descriptors:
            score_factor = float(desc.get("score_factor", 1.0))
            hit = {
                "receptor": desc["receptor"],
                "ligand": canonical,
                "mass": mass,
                "freq": freq,
                "score": mass * score_factor,   # simple scoring: mass * factor
                "target_cell_types": desc.get("target_cell_types", []),
            }
            hits.append(hit)
    return hits

# quick manual run when executing this file (handy for debugging)
if __name__ == "__main__":
    sample = [
        {"ligand":"CXCL10","mass":2.0,"freq":1},
        {"ligand":"IL12","mass":0.6,"freq":1},
        {"ligand":"S_RBD","mass":8.0,"freq":1},
        {"ligand":"MHC_PEPTIDE","mass":1.0,"freq":1}
    ]
    print("Sample hits:", match_receptors_from_summary(sample))

