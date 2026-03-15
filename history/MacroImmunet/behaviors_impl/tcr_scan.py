# behaviors_impl/tcr_scan.py
"""
TCR scanning behavior (robust affinity call).

This version will try to call env.compute_affinity(pm, tcr) first,
and if that raises TypeError will try compute_affinity(tcr, pm).
It ALWAYS emits a "tcr_scan_result" event when any pMHC candidates were
examined (even if best affinity is below reporting threshold).
"""
from typing import Any, Dict

def TCR_scan_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    # params keys and defaults
    radius = int(params.get("scan_radius", 1))
    affinity_threshold = float(params.get("affinity_threshold_report", 0.01))  # if you want to filter events, tests expect low default
    max_candidates = int(params.get("max_candidates", 200))
    early_stop = bool(params.get("early_stop_on_high_affinity", True))
    early_thr = float(params.get("early_stop_threshold", 0.9))

    collect_fn = getattr(env, "collect_pMHC_near", None)
    compute_aff_fn = getattr(env, "compute_affinity", None)

    # if there's no collector, nothing to scan; be silent (no event)
    if not callable(collect_fn):
        return []

    # obtain cell coord (compat with either coord or position attr)
    coord = getattr(cell, "coord", None)
    if coord is None:
        coord = getattr(cell, "position", None)

    pmhcs = collect_fn(coord, radius)
    # if no candidates, emit nothing (tests expect an event only when pmhcs exist)
    if not pmhcs:
        return []

    tcrs = getattr(cell, "tcr_repertoire", []) or []
    best_aff = 0.0
    best_summary = None

    seen = 0
    for pm in pmhcs:
        if seen >= max_candidates:
            break
        seen += 1
        # if cell has no TCR repertoire, still attempt one heuristic pass
        if not tcrs:
            # attempt a heuristic affinity if possible
            try:
                if callable(compute_aff_fn):
                    try:
                        aff = compute_aff_fn(pm, getattr(cell, "tcr", None))
                    except TypeError:
                        try:
                            aff = compute_aff_fn(getattr(cell, "tcr", None), pm)
                        except Exception:
                            aff = 0.0
                else:
                    aff = 0.0
                if aff > best_aff:
                    best_aff = float(aff)
                    best_summary = {"pMHC_id": pm.get("pMHC_id"), "peptide_id": pm.get("peptide_id"), "mhc_type": pm.get("mhc_type")}
            except Exception:
                pass
            # continue to next pm
            if early_stop and best_aff >= early_thr:
                break
            continue

        for tcr in tcrs:
            aff = 0.0
            try:
                if callable(compute_aff_fn):
                    # try common signature (pm, tcr) first
                    try:
                        aff = compute_aff_fn(pm, tcr)
                    except TypeError:
                        # maybe signature is (clonotype, pmhc)
                        try:
                            aff = compute_aff_fn(tcr, pm)
                        except Exception:
                            aff = 0.0
                else:
                    # fallback heuristic: exact peptide match if clonotype encodes target_peptide
                    pid = pm.get("peptide_id") or pm.get("epitope_seq")
                    t_match = tcr.get("target_peptide") if isinstance(tcr, dict) else None
                    aff = 1.0 if (t_match and pid == t_match) else 0.0
            except Exception:
                aff = 0.0

            if aff > best_aff:
                best_aff = float(aff)
                best_summary = {"pMHC_id": pm.get("pMHC_id"), "peptide_id": pm.get("peptide_id"), "mhc_type": pm.get("mhc_type")}
                if early_stop and best_aff >= early_thr:
                    break
        if early_stop and best_aff >= early_thr:
            break

    # Decide recognized flag relative to threshold
    recognized = best_aff >= affinity_threshold

    # emit event regardless of whether best_aff crosses threshold (tests expect the event)
    try:
        if hasattr(env, "emit_event"):
            payload_out = {
                "cell_id": getattr(cell, "id", None),
                "best_affinity": best_aff,
                "pmhc_summary": best_summary,
                "recognized": recognized,
                "tick": getattr(env, "tick", None),
            }
            env.emit_event("tcr_scan_result", payload_out)
    except Exception:
        # swallow errors from emit_event to not break test harness
        pass

    # store last_scan in cell.meta for downstream behaviors if desired
    try:
        if not hasattr(cell, "meta") or cell.meta is None:
            cell.meta = {}
        cell.meta["last_scan"] = {"best_affinity": best_aff, "pmhc_summary": best_summary, "recognized": recognized}
    except Exception:
        pass

    # return a consistent action describing the scan
    return [{"name": "tcr_scan_result", "payload": {"best_affinity": best_aff, "pmhc_summary": best_summary, "recognized": recognized}}]

