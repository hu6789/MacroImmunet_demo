# runner_ein/percell/th2_percell.py
"""
Th2 per-cell decision handler for runner_ein demo.

API:
    decide(cell, env, intent, params) -> list(actions)

Actions are dicts like:
    {"name": "secrete", "payload": {"substance": "IL4", "amount": X}}
    {"name": "differentiate", "payload": {"target_state": "Effector_Th2", "probability": P}}
    {"name": "noop"}  # optional

Expected cell interface (demo):
    cell.id, cell.coord, cell.tcr_repertoire (list of clonotypes)
    clonotype example: {"id":"cl1", "specificity": {"PepX","PepY"}}

Expected env helpers (demo):
    env.collect_pMHC_near(coord, radius=1) -> list of pmhc dicts
    env.compute_affinity(pm, tcr) -> float 0..1
    env.emit_event(name, payload)
"""
from typing import Any, Dict, List, Optional
import random

DEFAULTS = {
    "min_affinity_for_action": 0.2,   # affinity threshold to consider an activation
    "secrete_on_recognition": True,
    "secrete_amount": 1.0,
    "differentiate_prob_base": 0.2,   # base prob to differentiate into Th2 when recognized
    "require_co_stim": False,
    "co_stim_field": "Field_IL12",    # if require_co_stim True, check for IL12 low->reduce Th2
    "co_stim_thresh": 0.1,
}

def _get_peptides_from_intent(intent: Dict, env: Any, cell: Any) -> List[Dict]:
    """
    Try to get a list of pMHC dicts either from intent or via env helper.
    Normalize to list of dicts with at least 'peptide_id' and 'mhc_type'.
    """
    pmhcs = []
    if isinstance(intent, dict):
        p = intent.get("pmhc_summary") or intent.get("pmhc") or intent.get("pmhc_list")
        if p:
            # ensure list
            if isinstance(p, dict):
                pmhcs = [p]
            elif isinstance(p, list):
                pmhcs = p
    # fallback to env.collect_pMHC_near if available
    if not pmhcs and env and hasattr(env, "collect_pMHC_near"):
        try:
            coord = getattr(cell, "coord", None)
            if coord is not None:
                pmhcs = env.collect_pMHC_near(coord, radius=int(intent.get("scan_radius", 1)))
        except Exception:
            pmhcs = []
    # final normalization
    out = []
    for pm in pmhcs:
        if not isinstance(pm, dict):
            continue
        # canonical keys: peptide_id, mhc_type
        if "peptide_id" in pm:
            out.append(pm)
    return out

def _cell_has_matching_tcr(cell: Any, peptide_id: str) -> Optional[Dict]:
    """
    Check cell.tcr_repertoire for a clonotype that recognizes peptide_id.
    Return the clonotype dict if found, else None.
    """
    reps = getattr(cell, "tcr_repertoire", None)
    if not reps:
        return None
    # support various repertoire encodings
    for clon in reps:
        # clon may be dict or tuple; try to be permissive
        try:
            if isinstance(clon, dict):
                spec = clon.get("specificity", set()) or set()
                # allow string-specificity too
                if isinstance(spec, str):
                    if peptide_id == spec:
                        return clon
                else:
                    if peptide_id in spec:
                        return clon
            else:
                # maybe clon is a tuple like ("cl1", {"PepX"})
                try:
                    if isinstance(clon, (list, tuple)) and len(clon) >= 2:
                        spec = clon[1]
                        if isinstance(spec, str):
                            if peptide_id == spec:
                                return {"id": clon[0], "specificity": {spec}}
                        else:
                            if peptide_id in set(spec):
                                return {"id": clon[0], "specificity": set(spec)}
                except Exception:
                    continue
        except Exception:
            continue
    return None

def decide(cell: Any, env: Any, intent: Dict, params: Dict) -> List[Dict]:
    """
    Main percell decision entrypoint.
    Returns a list of action dicts to be consumed by orchestrator / scheduler.
    """
    p = {}
    p.update(DEFAULTS)
    if isinstance(params, dict):
        p.update(params)

    actions: List[Dict] = []
    try:
        pmhcs = _get_peptides_from_intent(intent, env, cell)
        chosen_pm = None
        chosen_clon = None
        best_aff = 0.0

        # inspect pMHCs and repertoire to find best match
        for pm in pmhcs:
            peptide_id = pm.get("peptide_id")
            if peptide_id is None:
                continue
            clon = _cell_has_matching_tcr(cell, peptide_id)
            if clon is None:
                # still we may compute a low affinity via env.compute_affinity if available
                if hasattr(env, "compute_affinity"):
                    try:
                        aff = env.compute_affinity(pm, {}) or 0.0
                    except Exception:
                        aff = 0.0
                else:
                    aff = 0.0
            else:
                # compute affinity using the clonotype (prefer clon dict)
                tcr_obj = clon
                if hasattr(env, "compute_affinity"):
                    try:
                        aff = env.compute_affinity(pm, tcr_obj) or 0.0
                    except Exception:
                        aff = 0.0
                else:
                    aff = 0.8  # heuristics: if clonotype matches, assume decent affinity
            if aff > best_aff:
                best_aff = aff
                chosen_pm = pm
                chosen_clon = clon

        # produce observable event about the percell decision inputs
        try:
            if env and hasattr(env, "emit_event"):
                env.emit_event("percell_decision", {"cell_id": getattr(cell, "id", None), "best_affinity": best_aff, "pmhc": (chosen_pm or None), "matched_clon": (getattr(chosen_clon, 'get', lambda k, d=None: None)('id', None) if isinstance(chosen_clon, dict) else None)})
        except Exception:
            pass

        # If best affinity below threshold -> nothing
        if best_aff < float(p.get("min_affinity_for_action", 0.2)):
            return []

        # Optionally check co-stimulation / cytokine context (IL-12 reduces Th2 likelihood)
        co_stim_ok = True
        if p.get("require_co_stim", False):
            # We interpret require_co_stim==True as requiring *low* IL12 (i.e. Th2 favors low IL12).
            # If IL12 present above threshold, then suppress Th2 differentiation.
            try:
                field = p.get("co_stim_field", "Field_IL12")
                coord = getattr(cell, "coord", None)
                if coord and env and hasattr(env, "collect_field_value_at"):
                    # if env helper exists, use it; else try env.space.fields directly (best-effort)
                    val = env.collect_field_value_at(field, coord)
                else:
                    # try best-effort: env.space? or cell.space?
                    val = None
                    # fallback: if intent includes field_value, use it
                    if isinstance(intent, dict) and intent.get("field_values", {}).get(field) is not None:
                        val = intent["field_values"][field]
                    # else give up and assume OK
                if val is not None and float(val) > float(p.get("co_stim_thresh", 0.1)):
                    co_stim_ok = False
            except Exception:
                co_stim_ok = True

        # Decide secrete action (Th2 secretes IL4) - we trigger secretion on recognition
        if p.get("secrete_on_recognition", True):
            amt = float(p.get("secrete_amount", 1.0))
            actions.append({"name": "secrete", "payload": {"substance": "IL4", "amount": amt}})

        # Decide differentiation probability: base * affinity (affinity boosts prob)
        base = float(p.get("differentiate_prob_base", 0.2))
        # scale with affinity between threshold and 1.0
        thresh = float(p.get("min_affinity_for_action", 0.2))
        affinity_scale = 0.0
        if best_aff > thresh:
            affinity_scale = (best_aff - thresh) / (1.0 - thresh) if (1.0 - thresh) > 0 else 1.0
        diff_prob = min(1.0, base + affinity_scale * (1.0 - base))
        # suppress if co_stim not ok (IL12 high) because IL12 pushes Th1 away from Th2
        if not co_stim_ok:
            diff_prob = diff_prob * 0.2

        # return differentiate action (or multiplex)
        actions.append({"name": "differentiate", "payload": {"target_state": "Effector_Th2", "probability": diff_prob, "reason": {"best_affinity": best_aff, "pmhc": chosen_pm}}})

        return actions

    except Exception as e:
        # defensive: emit error and return empty actions
        try:
            if env and hasattr(env, "emit_event"):
                env.emit_event("percell_error", {"reason": "th2_decide_exception", "cell_id": getattr(cell, "id", None), "error": str(e)})
        except Exception:
            pass
        return []

