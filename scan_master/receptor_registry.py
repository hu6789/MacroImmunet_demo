# scan_master/receptor_registry.py
"""
Receptor registry + matcher (defensive, canonicalize-first).

API:
 - match_receptors_from_summary(ligand_summary) -> list of receptor_hits
 - canonicalize_ligand(name) -> canonical name

This file is backward-compatible with the previous ligand_summary shape:
 [{'ligand': 'NAME', 'mass':..., 'freq':...}, ...]
and will also accept slightly different key names.
"""
from typing import List, Dict, Any, Optional

# ---- Ligand alias map (extendable) ----
LIGAND_ALIAS: Dict[str, str] = {
    "IL12": "IL12", "IL-12": "IL12",
    "IL2": "IL2", "IL-2": "IL2",
    "IFNG": "IFNG", "IFN-G": "IFNG",
    "TNF": "TNF",
    "CXCL10": "CXCL10", "CCL21": "CCL21",
    "MHC_PEPTIDE": "MHC_PEPTIDE", "PEPTIDE_MHC": "MHC_PEPTIDE",
    "PAMP": "PAMP_FRAG", "PAMP_FRAG": "PAMP_FRAG",
    "VIRAL_REPLICATING": "VIRAL_REPLICATING",
    "VIRUS": "VIRUS", "ANTIGEN": "ANTIGEN_PARTICLE", "ANTIGEN_PARTICLE": "ANTIGEN_PARTICLE", "AG_PARTICLE": "ANTIGEN_PARTICLE",
}

def canonicalize_ligand(name: str) -> str:
    if not isinstance(name, str):
        return str(name)
    if name in LIGAND_ALIAS:
        return LIGAND_ALIAS[name]
    # try uppercase trimmed fallback
    n = name.strip().upper()
    return LIGAND_ALIAS.get(n, n)


# ---- Receptor registry ----
RECEPTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    "IL12R": {"binds": ["IL12"], "target_cells": ["NAIVE_T", "TH1"]},
    "IL2R": {"binds": ["IL2"], "target_cells": ["NAIVE_T", "TH1", "CTL"]},
    "IFNGR": {"binds": ["IFNG"], "target_cells": ["CTL", "DC", "TH1"]},
    "TNFR": {"binds": ["TNF"], "target_cells": ["EPITHELIAL", "DC", "TH1"]},
    "CCR7": {"binds": ["CCL21"], "target_cells": ["DC", "NAIVE_T"]},
    "CXCR3": {"binds": ["CXCL10"], "target_cells": ["TH1", "CTL"]},
    "TCR": {"binds": ["MHC_PEPTIDE"], "target_cells": ["NAIVE_T", "TH1", "CTL"]},
    "PRR_SENSOR": {"binds": ["PAMP_FRAG", "VIRAL_REPLICATING"], "target_cells": ["EPITHELIAL", "DC"]},
    "ACE2": {"binds": ["VIRUS", "ANTIGEN_PARTICLE"], "target_cells": ["EPITHELIAL"]},
}

# ---- Matching function ----
def match_receptors_from_summary(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input: ligand_summary list with items containing 'ligand' key (or similar), mass and freq.
    Output: list of receptor hit dicts:
      {'receptor', 'ligand', 'mass', 'freq', 'score', 'target_cell_types'}
    Score heuristic: mass * (1 + sqrt(freq)) for freq>1 else mass
    """
    # defensive: normalize input to list of {ligand, mass, freq}
    canon_map: Dict[str, Dict[str, float]] = {}
    for item in (ligand_summary or []):
        # tolerant extraction
        lig = None
        if isinstance(item, dict):
            lig = item.get("ligand") or item.get("name") or item.get("type")
        else:
            lig = item
        if lig is None:
            continue
        canon = canonicalize_ligand(str(lig))
        try:
            mass = float(item.get("mass", 0.0)) if isinstance(item, dict) else 0.0
        except Exception:
            mass = 0.0
        try:
            freq = int(item.get("freq", 1)) if isinstance(item, dict) else 1
        except Exception:
            freq = 1
        if canon not in canon_map:
            canon_map[canon] = {"mass": 0.0, "freq": 0}
        canon_map[canon]["mass"] += mass
        canon_map[canon]["freq"] += freq

    hits: List[Dict[str, Any]] = []
    for rname, rmeta in RECEPTOR_REGISTRY.items():
        binds = rmeta.get("binds", []) or []
        for ligand in binds:
            if ligand in canon_map:
                m = canon_map[ligand]["mass"]
                f = canon_map[ligand]["freq"]
                score = m * (1.0 + (0.0 if f <= 1 else f ** 0.5))
                hits.append({
                    "receptor": rname,
                    "ligand": ligand,
                    "mass": m,
                    "freq": f,
                    "score": float(score),
                    "target_cell_types": list(rmeta.get("target_cells", []))
                })

    # sort by score desc
    hits.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return hits


# ---- quick smoke test ----
if __name__ == "__main__":
    sample = [
        {"ligand": "IL12", "mass": 0.6, "freq": 1},
        {"ligand": "CXCL10", "mass": 3.0, "freq": 2},
        {"ligand": "ANTIGEN", "mass": 8.0, "freq": 1},
        {"ligand": "MHC_PEPTIDE", "mass": 1.0, "freq": 1},
    ]
    for h in match_receptors_from_summary(sample):
        print(h)

