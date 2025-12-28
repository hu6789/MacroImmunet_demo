# scan_master/label_names.py
"""
MacroImmunet_demo — Label registry (consolidated, copy-safe)

- All labels used in the demo are declared here with consistent metadata
- Derived lists are computed at EOF so any LABEL_REGISTRY.update(...) above will be captured
- Fields: type, visible_to_scan, canonical, notes, half_life (ticks), allowed_sources

Utilities:
 - get_label_meta(name) -> dict (empty dict if not found)
 - is_entity_label(name, kinds=None) -> bool
 - classify_label_item(raw_label) -> { original, canonical, meta }
 - can_produce_label(cell_type, label_name) -> bool
 - pretty_classification(raw_label) -> str
"""
from typing import Dict, Any, List, Optional

LABEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # -------------------- CELLS --------------------
    "EPITHELIAL": {"type": "cell", "visible_to_scan": True, "canonical": "EPITHELIAL", "notes": "lung epithelial cell"},
    "DC":         {"type": "cell", "visible_to_scan": True, "canonical": "DC", "notes": "dendritic cell"},
    "MACROPHAGE": {"type": "cell", "visible_to_scan": True, "canonical": "MACROPHAGE", "notes": "macrophage (optional)"},
    "NAIVE_T":    {"type": "cell", "visible_to_scan": True, "canonical": "NAIVE_T", "notes": "naive T cell (LN)"},
    "TH1":        {"type": "cell", "visible_to_scan": True, "canonical": "TH1", "notes": "Th1 helper T cell"},
    "CTL":        {"type": "cell", "visible_to_scan": True, "canonical": "CTL", "notes": "cytotoxic T lymphocyte"},

    # -------------------- SUBSTANCES --------------------
    "ANTIGEN_PARTICLE": {"type": "substance", "visible_to_scan": True, "canonical": "ANTIGEN_PARTICLE", "notes": "discrete antigen / viral particle"},
    "VIRUS":            {"type": "substance", "visible_to_scan": True, "canonical": "VIRUS", "notes": "intact virus (entry-capable)"},
    "DEBRIS":           {"type": "substance", "visible_to_scan": True, "canonical": "DEBRIS", "notes": "cell debris / long-lived fragments"},
    "SPILLED_ANTIGEN":  {"type": "substance", "visible_to_scan": True, "canonical": "SPILLED_ANTIGEN", "notes": "antigen released from dead cell", "half_life": 40},
    "OWNED_ANTIGEN":    {"type": "substance", "visible_to_scan": True, "canonical": "OWNED_ANTIGEN", "notes": "antigen mass owned by a cell (owner field)", "half_life": 30},
    "OPSONIZED_PARTICLE": {"type": "substance", "visible_to_scan": True, "canonical": "OPSONIZED_PARTICLE", "notes": "antigen coated by antibody", "half_life": 30},

    # -------------------- FIELDS (cytokines / chemokines) --------------------
    "ANTIGEN_FIELD": {"type": "field", "visible_to_scan": True, "canonical": "ANTIGEN_FIELD", "notes": "continuous antigen concentration proxy"},
    "IL12":          {"type": "field", "visible_to_scan": True, "canonical": "IL12", "notes": "IL-12 (drives Th1 differentiation)", "half_life": 8},
    "IL2":           {"type": "field", "visible_to_scan": True, "canonical": "IL2", "notes": "IL-2 (supports T cell proliferation)", "half_life": 6},
    "IFNG":          {"type": "field", "visible_to_scan": True, "canonical": "IFNG", "notes": "IFN-gamma (activates/boosts CTL and DC)", "half_life": 8},
    "TNF":           {"type": "field", "visible_to_scan": True, "canonical": "TNF", "notes": "TNF-alpha (local inflammation)", "half_life": 10},
    "CCL21":         {"type": "field", "visible_to_scan": True, "canonical": "CCL21", "notes": "CCL21 (LN/DC migration)", "half_life": 12},
    "CXCL10":        {"type": "field", "visible_to_scan": True, "canonical": "CXCL10", "notes": "CXCL10/IP-10 (Th1/CTL chemoattractant)", "half_life": 12},

    # -------------------- SURFACE / PRESENTATION --------------------
    "MHC_I":       {"type": "surface", "visible_to_scan": True, "canonical": "MHC_I", "notes": "MHC class I peptide complex"},
    "MHC_II":      {"type": "surface", "visible_to_scan": True, "canonical": "MHC_II", "notes": "MHC class II peptide complex"},
    "MHC_PEPTIDE": {"type": "surface", "visible_to_scan": True, "canonical": "MHC_PEPTIDE", "notes": "MHC-bound peptide token (meta['epitope'] optional)", "half_life": 12},
    "TCR_PERTYPE": {"type": "surface", "visible_to_scan": True, "canonical": "TCR_PERTYPE", "notes": "T cell TCR genotype/type token", "half_life": 99999, "allowed_sources": ["NAIVE_T", "TH1", "CTL"]},
    "ACE2_PRESENT": {"type": "surface", "visible_to_scan": True, "canonical": "ACE2_PRESENT", "notes": "ACE2 expression marker (entry prone)", "half_life": 99999},

    # -------------------- INFECTION / PRR / INTERNAL SIGNALS --------------------
    "INFECTED":         {"type": "event", "visible_to_scan": True, "canonical": "INFECTED", "notes": "cell-level infection marker", "half_life": 10, "allowed_sources": ["EPITHELIAL", "DC"]},
    "VIRAL_REPLICATING":{"type": "event", "visible_to_scan": True, "canonical": "VIRAL_REPLICATING", "notes": "active intracellular replication marker", "half_life": 6},
    "PRR_ACTIVATED":    {"type": "event", "visible_to_scan": True, "canonical": "PRR_ACTIVATED", "notes": "pattern-recognition receptor activated", "half_life": 6},
    "PAMP_FRAG":        {"type": "substance", "visible_to_scan": True, "canonical": "PAMP_FRAG", "notes": "pathogen-associated molecular fragment (PRR trigger)"},

    # -------------------- EVENT / DAMAGE / KILL --------------------
    "DAMP":           {"type": "event", "visible_to_scan": True, "canonical": "DAMP", "notes": "danger-associated molecular pattern"},
    "DYING_PRE":      {"type": "event", "visible_to_scan": True, "canonical": "DYING_PRE", "notes": "early dying state (will spill)", "half_life": 4},
    "APOPTOTIC":      {"type": "event", "visible_to_scan": True, "canonical": "APOPTOTIC", "notes": "apoptotic stage", "half_life": 6},
    "NECROTIC":       {"type": "event", "visible_to_scan": True, "canonical": "NECROTIC", "notes": "necrotic event", "half_life": 6},
    "PERFORIN_PULSE": {"type": "event", "visible_to_scan": True, "canonical": "PERFORIN_PULSE", "notes": "CTL perforin release pulse", "half_life": 1},
    "DC_PRESENTING":  {"type": "event", "visible_to_scan": True, "canonical": "DC_PRESENTING", "notes": "DC actively presenting antigen", "half_life": 8},
    "CTL_ACTIVE":     {"type": "event", "visible_to_scan": True, "canonical": "CTL_ACTIVE", "notes": "CTL active/killing", "half_life": 6},
    "ANTIGEN_HANDOVER":{"type": "event", "visible_to_scan": True, "canonical": "ANTIGEN_HANDOVER", "notes": "antigen transfer/claim by DC", "half_life": 4},
    "HIGH_DANGER_ZONE":{"type": "event", "visible_to_scan": True, "canonical": "HIGH_DANGER_ZONE", "notes": "region-level amplified danger flag", "half_life": 12},
}

# -------------------- Derived lists (computed at EOF) --------------------
CELL_LABELS = [k for k, v in LABEL_REGISTRY.items() if v.get("type") == "cell"]
SUBSTANCE_LABELS = [k for k, v in LABEL_REGISTRY.items() if v.get("type") == "substance"]
FIELD_LABELS = [k for k, v in LABEL_REGISTRY.items() if v.get("type") == "field"]
SURFACE_LABELS = [k for k, v in LABEL_REGISTRY.items() if v.get("type") == "surface"]
EVENT_LABELS = [k for k, v in LABEL_REGISTRY.items() if v.get("type") == "event"]

# -------------------- Helpers --------------------
def get_label_meta(label_name: Optional[str]) -> Dict[str, Any]:
    """
    Return metadata dict for canonical label name (case-insensitive).
    Returns empty dict when not found.
    """
    if label_name is None:
        return {}
    name = str(label_name).upper()
    return LABEL_REGISTRY.get(name, {})


def is_entity_label(label_name: Optional[str], kinds: Optional[List[str]] = None) -> bool:
    meta = get_label_meta(label_name)
    if not meta:
        return False
    if kinds is None:
        return True
    return meta.get("type") in kinds


def classify_label_item(raw_label: Any) -> Dict[str, Any]:
    """
    Normalize a raw label (dict-like or object-like) to:
      { "original": raw_label_dict, "canonical": str, "meta": meta_dict }

    Defensive: accepts dict or object, fills sensible defaults.
    """
    # try to coerce raw_label into a dict-like minimal view for 'original'
    original = {}
    if isinstance(raw_label, dict):
        original = dict(raw_label)
        name = original.get('name') or original.get('label') or original.get('type') or ''
    else:
        # object-like: try attributes
        name = ''
        try:
            name = getattr(raw_label, "name", None) or getattr(raw_label, "label", None) or getattr(raw_label, "type", None) or ''
            # try to collect a dict representation if possible
            if hasattr(raw_label, "__dict__"):
                original = dict(getattr(raw_label, "__dict__", {}))
        except Exception:
            name = ''

    key = str(name).upper() if name is not None else ''

    if key in LABEL_REGISTRY:
        meta = LABEL_REGISTRY[key]
        canonical = meta.get('canonical', key)
    else:
        lkey = key.lower()
        # heuristics mapping common names to canonical labels
        if 'spike' in lkey or lkey.startswith('s_') or 'virus' in lkey or 'ag_' in lkey or 'antigen' in lkey:
            canonical = 'ANTIGEN_PARTICLE'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'mhc' in lkey or 'pept' in lkey or 'peptide' in lkey:
            # prefer MHC_PEPTIDE as canonical for peptide tokens
            canonical = 'MHC_PEPTIDE'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'il12' in lkey or 'il-12' in lkey:
            canonical = 'IL12'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'il2' in lkey or 'il-2' in lkey:
            canonical = 'IL2'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'ifn' in lkey:
            canonical = 'IFNG'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'tnf' in lkey:
            canonical = 'TNF'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'ccl21' in lkey:
            canonical = 'CCL21'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'cxcl10' in lkey or 'ip-10' in lkey or 'ip10' in lkey:
            canonical = 'CXCL10'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'damp' in lkey or 'danger' in lkey:
            canonical = 'DAMP'
            meta = LABEL_REGISTRY.get(canonical, {})
        elif 'perforin' in lkey:
            canonical = 'PERFORIN_PULSE'
            meta = LABEL_REGISTRY.get(canonical, {})
        else:
            canonical = 'DEBRIS'
            meta = LABEL_REGISTRY.get(canonical, {})

    # ensure meta is a dict
    meta = dict(meta or {})

    return {
        "original": original,
        "canonical": canonical,
        "meta": meta
    }


def can_produce_label(cell_type: str, label_name: str) -> bool:
    meta = get_label_meta(label_name)
    if not meta:
        return False
    allowed = meta.get('allowed_sources')
    if not allowed:
        return True
    return cell_type in allowed


def pretty_classification(raw_label: Any) -> str:
    c = classify_label_item(raw_label)
    nm = c['original'].get('name') or c['original'].get('label') or "?"
    return f"{nm} -> {c['canonical']} ({c['meta'].get('type','?')})"


# -------------------- Quick smoke test when run as script --------------------
if __name__ == "__main__":
    print("=== LABEL REGISTRY SAMPLE ===")
    for k in list(LABEL_REGISTRY.keys())[:12]:
        print(k, "->", LABEL_REGISTRY[k]['type'])

    examples = [
        {"name": "S_RBD", "mass": 10.0},
        {"name": "virus_particle", "mass": 5.0},
        {"name": "mhc_i_pep", "mass": 1.0},
        {"name": "IL-12", "mass": 0.5},
        {"name": "PERFORIN", "mass": 1.0},
        {"name": "unknown_stuff", "mass": 2.0},
    ]
    for ex in examples:
        print(pretty_classification(ex))

