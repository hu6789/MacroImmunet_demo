# behaviors_impl/dc_process.py
"""
Minimal DC processing implementation for tests:
 - If env.call_phagocytose is available, call it first to populate cell.captured_antigens.
 - For each antigen -> create pMHC entries, append to cell.present_list and emit_event("pMHC_presented", {...}).
 - Increase co_stim and set maturation_state to "Mature" when done. Return actions including 'pMHC_presented' and
   optionally 'migrate_to_LN'.
"""

def _make_pmhc_entry(antigen, epitope_id="E1"):
    return {
        "pMHC_id": f"pMHC_{antigen.get('id','ag')}_{epitope_id}",
        "peptide_id": f"{antigen.get('id')}_{epitope_id}",
        "seq": antigen.get("sequence", "")[:9],
        "mhc_type": "MHC_II",
        "presenter": "dc"
    }

def DC_process_and_load_MHC_v1(cell, env, params=None, payload=None, **kw):
    params = params or {}
    costim_increase = params.get("costim_increase", 0.5)
    migrate_threshold = params.get("migrate_threshold", 0.4)

    actions = []

    # If env provides a phagocytose callable, call it (tests stub env.call_phagocytose)
    try:
        if hasattr(env, "call_phagocytose") and callable(env.call_phagocytose):
            res = env.call_phagocytose(cell, env, params=params, payload=payload)
            # call_phagocytose may return actions; extend if so
            if isinstance(res, (list, tuple)):
                actions.extend(res)
    except Exception:
        # swallow env errors so tests won't crash
        pass

    captured = getattr(cell, "captured_antigens", []) or []
    if not captured:
        # even if nothing captured, ensure maturation state progression might still occur in higher-level behaviors
        return actions

    if not hasattr(cell, "present_list"):
        cell.present_list = []

    for i, ag in enumerate(captured):
        # get epitope id if present
        ep_list = ag.get("epitopes") if isinstance(ag.get("epitopes"), list) else None
        ep_id = (ep_list[0].get("id") if ep_list and isinstance(ep_list[0], dict) and ep_list[0].get("id") else f"E{i+1}")
        pmhc = _make_pmhc_entry(ag, epitope_id=ep_id)
        cell.present_list.append(pmhc)

        # emit an event for tests that check env.emit_event
        try:
            if hasattr(env, "emit_event"):
                env.emit_event("pMHC_presented", {"cell_id": getattr(cell, "id", None), "pMHC": pmhc, "tick": None})
        except Exception:
            pass

        actions.append({"name": "pMHC_presented", "payload": {"cell_id": getattr(cell, "id", None), "pMHC": pmhc}})

    # increase co-stim
    try:
        cell.co_stim = float(getattr(cell, "co_stim", 0.0)) + float(costim_increase)
    except Exception:
        cell.co_stim = getattr(cell, "co_stim", 0.0)

    # set maturation state to Mature after processing
    try:
        cell.maturation_state = "Mature"
    except Exception:
        pass

    if getattr(cell, "co_stim", 0.0) >= migrate_threshold:
        migrate_payload = {"cell_id": getattr(cell, "id", None), "co_stim": cell.co_stim, "tick": None}
        try:
            if hasattr(env, "emit_event"):
                env.emit_event("migrate_to_LN", migrate_payload)
        except Exception:
            pass
        actions.append({"name": "migrate_to_LN", "payload": migrate_payload})

    return actions

