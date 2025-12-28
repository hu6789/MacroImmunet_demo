# scan_master/receptor_library.py
"""
Receptor library wrapper for MacroImmunet_demo.

Provides a stable, testable match API on top of the RECEPTOR_REGISTRY.
Features:
 - optional type-checking (field / event / surface / substance)
 - min_score / top_k filtering
 - deterministic sorting by score (desc, tie-break by receptor name)
 - simple pluggable class (ReceptorLibrary) to allow later replacement
 - backward-compatible function aliases
"""

from typing import List, Dict, Any, Optional
from math import sqrt

from .receptor_registry import RECEPTOR_REGISTRY
from .label_names import get_label_meta

# -------------------------
# Scoring / helpers
# -------------------------
def _score_for_mass_freq(mass: float, freq: int) -> float:
    """
    Simple scoring function used across the demo:
      score = mass * (1 + sqrt(freq))  (freq contributes weakly)
    Keep it here to centralize scoring.
    """
    if freq <= 1:
        return float(mass)
    return float(mass) * (1.0 + (freq ** 0.5))


def _type_of_ligand(ligand_name: str) -> Optional[str]:
    """Return label type ('field','surface','substance','event','cell',...) or None."""
    meta = get_label_meta(ligand_name)
    if not meta:
        return None
    return meta.get("type")


# -------------------------
# Core matcher (ext)
# -------------------------
def match_receptors_from_summary_ext(
    ligand_summary: List[Dict[str, Any]],
    require_type_match: bool = False,
    accepted_label_types: Optional[List[str]] = None,
    min_score: float = 0.0,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Match receptors against an aggregator ligand_summary.

    ligand_summary: list of {'ligand': canonical_name, 'mass': float, 'freq': int}
    require_type_match: if True, only match when the ligand's label type (from label_names)
                        is in accepted_label_types.
    accepted_label_types: e.g. ['field','surface','substance','event'] - used only if require_type_match True
    min_score: filter out hits below this score
    top_k: return only top_k hits (by score)

    Returns list of hits in the form:
      {
        "receptor": str,
        "ligand": str,
        "mass": float,
        "freq": int,
        "score": float,
        "target_cell_types": [...],
        "ligand_type": Optional[str]
      }
    """
    # quick map for lookup
    ligand_map = {item['ligand']: item for item in ligand_summary}
    hits: List[Dict[str, Any]] = []

    for rname, rmeta in RECEPTOR_REGISTRY.items():
        binds = rmeta.get('binds', [])
        target_cells = list(rmeta.get('target_cells', []))
        for ligand in binds:
            if ligand not in ligand_map:
                continue

            # type check if requested
            lmeta_type = _type_of_ligand(ligand)
            if require_type_match and accepted_label_types:
                if lmeta_type not in accepted_label_types:
                    continue

            item = ligand_map[ligand]
            mass = float(item.get('mass', 0.0))
            freq = int(item.get('freq', 0))
            score = _score_for_mass_freq(mass, freq)
            if score < float(min_score):
                continue

            hit = {
                "receptor": rname,
                "ligand": ligand,
                "mass": mass,
                "freq": freq,
                "score": score,
                "target_cell_types": target_cells,
                "ligand_type": lmeta_type
            }
            hits.append(hit)

    # deterministic sort: score desc, break ties by receptor name
    hits.sort(key=lambda x: (-x['score'], x['receptor']))

    if top_k is not None and top_k > 0:
        return hits[:top_k]
    return hits


# -------------------------
# Convenience wrappers
# -------------------------
def match_receptors_from_summary(ligand_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Backwards-compatible simple API used by many demo components:
      - matches all ligand types with default scoring and no top_k/min filters
    """
    return match_receptors_from_summary_ext(ligand_summary)


def match_receptors_field_only(ligand_summary: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """Match only ligands whose label type == 'field' (e.g. cytokines / chemokines)."""
    fields = [it for it in ligand_summary if _type_of_ligand(it.get("ligand")) == "field"]
    return match_receptors_from_summary_ext(fields, **kwargs)


def match_receptors_surface_only(ligand_summary: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """Match only ligands whose label type == 'surface' (e.g. MHC_PEPTIDE)."""
    surfaces = [it for it in ligand_summary if _type_of_ligand(it.get("ligand")) == "surface"]
    return match_receptors_from_summary_ext(surfaces, **kwargs)


# keep ext alias name for compatibility
match_receptors_from_summary_ext = match_receptors_from_summary_ext


# -------------------------
# Pluggable class wrapper
# -------------------------
class ReceptorLibrary:
    """
    Simple object wrapper around match_receptors_from_summary_ext.
    Keeps config defaults and offers a .match(...) method.
    """

    def __init__(self, require_type_match: bool = False, accepted_label_types: Optional[List[str]] = None):
        self.require_type_match = require_type_match
        self.accepted_label_types = accepted_label_types

    def match(
        self,
        ligand_summary: List[Dict[str, Any]],
        min_score: float = 0.0,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return match_receptors_from_summary_ext(
            ligand_summary,
            require_type_match=self.require_type_match,
            accepted_label_types=self.accepted_label_types,
            min_score=min_score,
            top_k=top_k,
        )


# -------------------------
# Module smoke / demo
# -------------------------
if __name__ == "__main__":
    sample = [
        {"ligand": "IL12", "mass": 0.6, "freq": 1},
        {"ligand": "CXCL10", "mass": 3.0, "freq": 2},
        {"ligand": "ANTIGEN_PARTICLE", "mass": 8.0, "freq": 1},
        {"ligand": "MHC_PEPTIDE", "mass": 1.0, "freq": 1},
    ]
    lib = ReceptorLibrary()
    hits = lib.match(sample)
    print("=== receptor hits (default) ===")
    for h in hits:
        print(h)
    print("=== receptor hits (field-only) ===")
    lib2 = ReceptorLibrary(require_type_match=True, accepted_label_types=['field'])
    print(lib2.match(sample))

