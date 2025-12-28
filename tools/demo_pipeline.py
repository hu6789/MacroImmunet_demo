# scan_master/receptor_library.py
"""
Lightweight receptor library wrapper for MacroImmunet_demo.

This module wraps the lower-level receptor registry matcher and provides
convenient filtering functions and a stable API for the demo pipeline:

Public API:
 - match_receptors_from_summary(ligand_summary) -> list of receptor_hits
 - match_receptors_field_only(ligand_summary)
 - match_receptors_surface_only(ligand_summary)
 - summarize_ligands_by_type(ligand_summary) -> dict mapping type -> list(items)
"""

from typing import List, Dict, Any
from scan_master import receptor_registry
from scan_master.label_names import get_label_meta

__all__ = [
    "match_receptors_from_summary",
    "match_receptors_field_only",
    "match_receptors_surface_only",
    "summarize_ligands_by_type",
]

def _ensure_summary_shape(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure ligand_summary is a list of dicts with keys ligand/mass/freq.
    Accepts both canonical-ligand entries and raw items; returns normalized list.
    """
    out = []
    for it in ligand_summary:
        if not isinstance(it, dict):
            continue
        k = it.get("ligand") or it.get("name") or it.get("canonical")
        if k is None:
            continue
        out.append({
            "ligand": str(k),
            "mass": float(it.get("mass", 0.0)),
            "freq": int(it.get("freq", 0))
        })
    return out

def match_receptors_from_summary(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Primary wrapper API used by demo_pipeline.
    Delegates to receptor_registry.match_receptors_from_summary after normalization.
    """
    ls = _ensure_summary_shape(ligand_summary)
    # Use the registry's matcher
    hits = receptor_registry.match_receptors_from_summary(ls)
    return hits

def summarize_ligands_by_type(ligand_summary: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize ligand_summary items by their LABEL_REGISTRY type (field/surface/substance/event/cell).
    Returns a dict: { 'field': [...], 'surface': [...], 'substance': [...], 'event': [...], 'cell': [...] }
    Items keep the 'ligand','mass','freq' keys.
    """
    ls = _ensure_summary_shape(ligand_summary)
    buckets = {"field": [], "surface": [], "substance": [], "event": [], "cell": [], "unknown": []}
    for it in ls:
        meta = get_label_meta(it["ligand"])
        if not meta:
            buckets["unknown"].append(it)
            continue
        t = meta.get("type", "unknown")
        if t not in buckets:
            buckets["unknown"].append(it)
        else:
            buckets[t].append(it)
    return buckets

def match_receptors_field_only(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run matching but only for ligands classified as 'field' in label registry
    (e.g., cytokines / chemokines).
    """
    buckets = summarize_ligands_by_type(ligand_summary)
    field_ls = buckets.get("field", [])
    return match_receptors_from_summary(field_ls)

def match_receptors_surface_only(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run matching but only for surface ligands (e.g., MHC_PEPTIDE, MHC_I, TCR token markers).
    """
    buckets = summarize_ligands_by_type(ligand_summary)
    surf_ls = buckets.get("surface", [])
    return match_receptors_from_summary(surf_ls)

# quick smoke when invoked directly
if __name__ == "__main__":
    sample = [
        {"ligand":"IL12","mass":0.6,"freq":1},
        {"ligand":"CXCL10","mass":3.0,"freq":2},
        {"ligand":"ANTIGEN_PARTICLE","mass":8.0,"freq":1},
        {"ligand":"MHC_PEPTIDE","mass":1.0,"freq":1},
    ]
    print("=== receptor_library smoke ===")
    print("all hits:", match_receptors_from_summary(sample))
    print("field-only hits:", match_receptors_field_only(sample))
    print("surface-only hits:", match_receptors_surface_only(sample))

