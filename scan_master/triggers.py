# scan_master/triggers.py
"""
Rule-based trigger engine for MacroImmunet_demo.

This module exposes `apply_triggers_to_region(space, region_id, ligand_summary, spectrum, current_tick)`
and contains a collection of small, readable trigger rules. It purposely avoids importing
the module itself (no self-import) to prevent circular imports.
"""

from typing import List, Dict, Any, Tuple
import uuid
import math

from .label_names import FIELD_LABELS, EVENT_LABELS, SURFACE_LABELS, get_label_meta, classify_label_item
from .node_builder import build_nodes_from_summary
from .receptor_registry import match_receptors_from_summary

# Tunables (demo)
HOTSPOT_ANTIGEN_MASS = 8.0
HOTSPOT_DAMP_COUNT = 1
ANTIGEN_HANDOVER_MASS = 3.0
DC_PRESENT_MIN_ANTIGEN = 1.0

def _mk_emitted(name: str, mass: float = 1.0, created_tick: int = 0, owner: str = None, meta: dict = None):
    return {"id": str(uuid.uuid4()), "name": name, "mass": float(mass), "created_tick": int(created_tick), "owner": owner, "meta": meta or {}}

# ---------------------- Basic small rules ----------------------

def hotspot_rule(ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any], current_tick: int) -> List[Dict[str,Any]]:
    emitted = []
    total_antigen = sum(item['mass'] for item in ligand_summary if item['ligand'] in ('ANTIGEN_PARTICLE','ANTIGEN_FIELD','SPILLED_ANTIGEN'))
    num_damp = spectrum.get('num_damp', 0)
    if total_antigen >= HOTSPOT_ANTIGEN_MASS or num_damp >= HOTSPOT_DAMP_COUNT:
        emitted.append(_mk_emitted("HIGH_DANGER_ZONE", mass=1.0, created_tick=current_tick, meta={"reason":"antigen_or_damp_hotspot"}))
    return emitted

def chemotaxis_field_rule(ligand_summary: List[Dict[str, Any]], current_tick: int) -> List[Dict[str,Any]]:
    emitted = []
    for key in ("CXCL10","CCL21"):
        item = next((x for x in ligand_summary if x['ligand'] == key), None)
        if item and item['mass'] > 0:
            # re-emit / hint the field so Space contains an explicit field label
            emitted.append(_mk_emitted(key, mass=item['mass'], created_tick=current_tick, meta={"hint":"field"}))
    return emitted

def antigen_entry_rule(space, region_id: str, ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any], current_tick: int) -> List[Dict[str,Any]]:
    emitted = []
    has_virus_mass = sum(x['mass'] for x in ligand_summary if x['ligand'] in ('VIRUS','ANTIGEN_PARTICLE')) > 0
    if not has_virus_mass:
        return emitted
    # check for ACE2 marker in live labels (region)
    region_labels = space.get_labels(region_id)
    ace2_present = any((str(l.get("name")).upper() == "ACE2_PRESENT") or (l.get("meta",{}).get("token")=="ACE2_PRESENT") for l in region_labels)
    if ace2_present:
        emitted.append(_mk_emitted("INFECTED", mass=1.0, created_tick=current_tick, meta={"reason":"entry_via_ACE2"}))
        # spawn replication marker
        emitted.append(_mk_emitted("VIRAL_REPLICATING", mass=1.0, created_tick=current_tick, meta={"note":"demo_replication"}))
    return emitted

def prr_activation_rule(ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any], current_tick: int) -> List[Dict[str,Any]]:
    emitted = []
    infected = any(item['ligand'] in ('INFECTED','VIRAL_REPLICATING','PAMP_FRAG','VIRAL_RNA_SIGNAL') for item in ligand_summary)
    if infected:
        emitted.append(_mk_emitted("PRR_ACTIVATED", mass=1.0, created_tick=current_tick))
        # simple cytokine seeding
        emitted.append(_mk_emitted("IFNG", mass=0.4, created_tick=current_tick))
        emitted.append(_mk_emitted("IL12", mass=0.6, created_tick=current_tick))
    return emitted

# ---------------------- Antigen handover / presentation ----------------------

def antigen_handover_rule(space, region_id: str, ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any], current_tick: int) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]]]:
    """
    If enough antigen present and DC exists in region, emit handover + owned antigen
    and generate a node request to sample antigen (Antigen_sampling).
    """
    emitted = []
    node_requests = []
    total_antigen = sum(item['mass'] for item in ligand_summary if item['ligand'] in ('ANTIGEN_PARTICLE','SPILLED_ANTIGEN','OWNED_ANTIGEN'))
    if total_antigen < ANTIGEN_HANDOVER_MASS:
        return emitted, node_requests

    region_labels = space.get_labels(region_id)
    # find a DC candidate
    dc_candidates = [l for l in region_labels if (str(l.get("name")).upper() == "DC" or l.get("meta",{}).get("cell_type")=="DC")]
    if dc_candidates:
        dc = dc_candidates[0]
        owner_id = dc.get("id") or ("DC_" + str(uuid.uuid4())[:8])
        emitted.append(_mk_emitted("ANTIGEN_HANDOVER", mass=1.0, created_tick=current_tick, meta={"owner": owner_id}))
        emitted.append(_mk_emitted("OWNED_ANTIGEN", mass=min(total_antigen, 10.0), created_tick=current_tick, owner=owner_id))
        emitted.append(_mk_emitted("MHC_PEPTIDE", mass=1.0, created_tick=current_tick, owner=owner_id, meta={"epitope":"E_demo"}))
        emitted.append(_mk_emitted("DC_PRESENTING", mass=1.0, created_tick=current_tick, owner=owner_id))
        node_requests.append({
            "node_type": "Antigen_sampling",
            "inputs": {"ligand":"ANTIGEN_PARTICLE","mass":total_antigen},
            "targets": ["DC"],
            "priority": 2.0
        })
    else:
        # still emit handover attempt (no owner)
        emitted.append(_mk_emitted("ANTIGEN_HANDOVER", mass=1.0, created_tick=current_tick, meta={"owner": None}))
    return emitted, node_requests

# ---------------------- MHC-TCR pairing (improved to see live emitted MHC) ----------------------

def mhc_tcr_pairing_rule(space, region_id: str, ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any], current_tick: int) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]]]:
    """
    If MHC_PEPTIDE exists (with meta.epitope) and a TCR_PERTYPE token is visible (means there are T cells of a given genotype),
    generate Tcell_antigen_contact and Tcell_prime node_requests to simulate adaptive contact.

    This function looks at both ligand_summary (pre-trigger snapshot) and the live Space labels (to see MHC emitted earlier in the same run).
    """
    emitted = []
    node_requests = []

    # 1) try to find MHC_PEPTIDE in the ligand_summary (pre-computed)
    mhc_items = [i for i in ligand_summary if i['ligand'] == 'MHC_PEPTIDE']

    # 2) if none found, also inspect live space labels in the region (covers MHC emitted earlier and written into Space)
    if not mhc_items:
        region_labels_live = space.get_labels(region_id)
        mhc_labels_live = [l for l in region_labels_live if str(l.get("name")).upper() == "MHC_PEPTIDE" or l.get("meta", {}).get("canonical") == "MHC_PEPTIDE"]
        if mhc_labels_live:
            # normalize into same summary-like dict structure (mass/freq)
            mhc_items = []
            for ml in mhc_labels_live:
                mass = float(ml.get("mass", 1.0))
                mhc_items.append({"ligand": "MHC_PEPTIDE", "mass": mass, "freq": 1, "original": ml})

    if not mhc_items:
        return emitted, node_requests

    # check region for TCR_PERTYPE tokens (live)
    region_labels = space.get_labels(region_id)
    tcr_tokens = [l for l in region_labels if str(l.get("name")).upper() == "TCR_PERTYPE" or l.get("meta",{}).get("token")=="TCR_PERTYPE"]
    if not tcr_tokens:
        return emitted, node_requests

    # for demo: create node_requests per mhc token
    for m in mhc_items:
        mass = float(m.get("mass", 1.0))
        node_requests.append({
            "node_type": "Tcell_antigen_contact",
            "inputs": {"ligand":"MHC_PEPTIDE","mass":mass},
            "targets": ["NAIVE_T","CTL"],
            "priority": 3.0 + 0.5 * math.log1p(mass)
        })
        # prime node if IL12 present in ligand_summary OR in live region labels
        il12_present = any(x['ligand']=='IL12' for x in ligand_summary)
        if not il12_present:
            # also check live space labels for IL12
            il12_present = any(str(l.get("name")).upper()=="IL12" for l in region_labels)
        if il12_present:
            node_requests.append({
                "node_type": "Tcell_prime",
                "inputs": {"ligand":"MHC_PEPTIDE","mass":mass},
                "targets": ["NAIVE_T","TH1"],
                "priority": 2.0
            })
        # also emit a DC_PRESENTING hint if not already present
        emitted.append(_mk_emitted("DC_PRESENTING", mass=1.0, created_tick=current_tick, meta={"reason":"mhc_tcr_pairing"}))

    return emitted, node_requests

# ---------------------- receptor-based node builder (bridge) ----------------------

def receptor_based_nodes_rule(ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any]) -> List[Dict[str,Any]]:
    node_requests = []
    try:
        receptor_hits = match_receptors_from_summary(ligand_summary)
        built = build_nodes_from_summary(ligand_summary, receptor_hits)
        if built:
            node_requests.extend(built)
    except Exception:
        # keep triggers robust to other module errors in demo
        pass
    return node_requests

# ---------------------- orchestrator ----------------------

def apply_triggers_to_region(space, region_id: str, ligand_summary: List[Dict[str, Any]], spectrum: Dict[str, Any], current_tick: int) -> Dict[str,Any]:
    """
    Run all triggers for a region. Returns dict:
      {"emitted": [labels...], "node_requests": [node dicts...]}

    Emitted labels are also written to space (space.add_label) for downstream use.
    """
    emitted: List[Dict[str,Any]] = []
    node_requests: List[Dict[str,Any]] = []

    # rule order matters (hotspot -> chemokine -> entry -> prr -> handover -> pairing -> receptor nodes)
    # 1) early rules
    emitted += hotspot_rule(ligand_summary, spectrum, current_tick)
    emitted += chemotaxis_field_rule(ligand_summary, current_tick)
    emitted += antigen_entry_rule(space, region_id, ligand_summary, spectrum, current_tick)
    emitted += prr_activation_rule(ligand_summary, spectrum, current_tick)

    # 2) antigen handover (this emits MHC_PEPTIDE which pairing relies on)
    hand_emitted, hand_nodes = antigen_handover_rule(space, region_id, ligand_summary, spectrum, current_tick)
    emitted += hand_emitted
    node_requests += hand_nodes

    # ---- CRITICAL: write handover-emitted labels to space immediately so pairing can see them ----
    # only write what was produced by handover (avoid duplicate writes later)
    for lab in hand_emitted:
        try:
            space.add_label(region_id, lab)
        except Exception:
            pass

    # 3) pairing rule (now can see MHC_PEPTIDE if produced by handover)
    pair_emitted, pair_nodes = mhc_tcr_pairing_rule(space, region_id, ligand_summary, spectrum, current_tick)
    emitted += pair_emitted
    node_requests += pair_nodes

    # 4) receptor-based nodes as final step
    node_requests += receptor_based_nodes_rule(ligand_summary, spectrum)

    # 5) write remaining emitted labels to Space (avoid double-write for hand_emitted above)
    # write all emitted that are not in hand_emitted (compare by id)
    hand_ids = set(l.get("id") for l in hand_emitted)
    for lab in emitted:
        if lab.get("id") in hand_ids:
            continue
        try:
            space.add_label(region_id, lab)
        except Exception:
            pass

    return {"emitted": emitted, "node_requests": node_requests}

