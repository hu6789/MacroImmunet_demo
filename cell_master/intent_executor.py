# cell_master/intent_executor.py
"""
Intent executor for the Step3/Step4 demo.

This module executes intents (phagocytose, pMHC_presented, activate_tcell, ...)
and writes resulting labels into the provided `space` in a robust/compatible way.

It favors these add_label signatures (in order):
 - space.add_label(region_id, lab)
 - space.add_label(lab, region_id)
 - space.add_label(lab)
If none exist it will try `space._local_labels` or `space.labels` as last resorts.
"""

from typing import Any, Dict, List, Optional
import time
import copy


def _robust_add_label(space: Any, region_id: Optional[str], lab: Dict[str, Any]) -> None:
    """Try several plausible signatures to register a label in `space`."""
    # 1) space.add_label(region_id, lab)
    try:
        fn = getattr(space, "add_label", None)
        if callable(fn):
            try:
                # preferred: (region_id, lab)
                fn(region_id, lab)
                return
            except TypeError:
                # maybe signature is (lab, region_id) or (lab,)
                try:
                    fn(lab, region_id)
                    return
                except TypeError:
                    try:
                        fn(lab)
                        return
                    except TypeError:
                        pass
            except Exception:
                # other errors, fallthrough to other strategies
                pass
    except Exception:
        pass

    # 2) try space.register_label / push_label variants
    for alt in ("register_label", "push_label", "register_labels"):
        fn = getattr(space, alt, None)
        if callable(fn):
            try:
                fn(lab)
                return
            except Exception:
                continue

    # 3) try _local_labels (dict keyed by region or list)
    try:
        if hasattr(space, "_local_labels"):
            ll = getattr(space, "_local_labels")
            if isinstance(ll, dict) and region_id is not None:
                lst = ll.setdefault(region_id, [])
                # update or append
                for i, e in enumerate(list(lst)):
                    if isinstance(e, dict) and e.get("id") == lab.get("id"):
                        lst[i] = lab
                        break
                else:
                    lst.append(lab)
                return
            if isinstance(ll, list):
                for i, e in enumerate(list(ll)):
                    if isinstance(e, dict) and e.get("id") == lab.get("id"):
                        ll[i] = lab
                        break
                else:
                    ll.append(lab)
                return
    except Exception:
        pass

    # 4) try top-level space.labels list
    try:
        if hasattr(space, "labels"):
            labs = getattr(space, "labels")
            if isinstance(labs, list):
                for i, e in enumerate(list(labs)):
                    if isinstance(e, dict) and e.get("id") == lab.get("id"):
                        labs[i] = lab
                        break
                else:
                    labs.append(lab)
                return
    except Exception:
        pass

    # nothing worked — swallow silently (space may be read-only)
    return


def _normalize_epitope(ep_raw: Any, space: Any, region_id: Optional[str]) -> Dict[str, Any]:
    """
    Normalize epitope field into dict {'seq': ...}.

    - If ep_raw is dict: return as-is (shallow-copied).
    - If ep_raw is string:
        - If it's 'ANTIGEN_PARTICLE' or similar, try to find an ANTIGEN_PARTICLE label
          in the space (within region_id) and extract its first epitope seq.
        - Otherwise treat the string as the peptide sequence.
    - Fallback to {'seq': 'UNKNOWN'}.
    """
    if isinstance(ep_raw, dict):
        return copy.deepcopy(ep_raw)

    if isinstance(ep_raw, str):
        key = ep_raw.strip()
        if key == "":
            return {"seq": "UNKNOWN"}

        # heuristics for placeholder token
        token = key.upper()
        if token in ("ANTIGEN_PARTICLE", "ANTIGEN", "VIRUS"):
            # try to find an antigen label in the region and extract first epitope
            try:
                labels = []
                get_labels = getattr(space, "get_labels", None)
                if callable(get_labels):
                    try:
                        # some get_labels expect just region_id, some accept none
                        labels = get_labels(region_id)
                    except TypeError:
                        labels = get_labels()
                elif hasattr(space, "_local_labels"):
                    ll = getattr(space, "_local_labels")
                    if isinstance(ll, dict) and region_id is not None:
                        labels = ll.get(region_id, []) or []
                    elif isinstance(ll, list):
                        labels = ll
                elif hasattr(space, "labels"):
                    labels = getattr(space, "labels") or []
                # scan for antigen labels
                for L in labels:
                    try:
                        lm = {}
                        if isinstance(L, dict):
                            lm = L.get("meta", {}) or {}
                        else:
                            lm = getattr(L, "meta", {}) or {}
                        if (lm.get("type") or "").upper() == "ANTIGEN_PARTICLE":
                            # try common epitope locations
                            eps = lm.get("epitopes") or lm.get("epitope")
                            if isinstance(eps, list) and eps:
                                first = eps[0]
                                if isinstance(first, dict) and first.get("seq"):
                                    return {"seq": first.get("seq")}
                                elif isinstance(first, str):
                                    return {"seq": first}
                            if isinstance(eps, dict) and eps.get("seq"):
                                return {"seq": eps.get("seq")}
                            # fallback to any sequence-like field
                            if isinstance(lm.get("epitopes"), str):
                                return {"seq": lm.get("epitopes")}
                    except Exception:
                        continue
            except Exception:
                pass
            # if not found, fallthrough to use token as seq
            return {"seq": key}

        # default: assume provided string is the peptide sequence
        return {"seq": key}

    # if it's a list with epitope dicts, take first
    if isinstance(ep_raw, (list, tuple)) and ep_raw:
        first = ep_raw[0]
        if isinstance(first, dict) and first.get("seq"):
            return {"seq": first.get("seq")}
        if isinstance(first, str):
            return {"seq": first}

    # unknown type -> fallback
    return {"seq": "UNKNOWN"}


def execute_intents(space: Any, region_id: str, intents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Execute a list of intents against `space` in region `region_id`.
    Returns a list of event dicts describing what happened.
    """
    events: List[Dict[str, Any]] = []

    for intent in intents:
        itype = intent.get("intent_type") or intent.get("name")
        meta = intent.get("meta", {}) or {}

        # -------- phagocytose: DC picks antigen (no label produced here) -------
        if itype == "phagocytose":
            events.append({
                "name": "phagocytose",
                "coord": intent.get("coord"),
                "targets": intent.get("targets"),
                "meta": meta
            })

        # -------- pMHC_presented: produce an MHC_PEPTIDE label --------------
        elif itype == "pMHC_presented":
            # make a unique id for pMHC
            tstamp = int(time.time())
            source = meta.get("source_node") or meta.get("origin") or "unknown"
            mhc_id = f"mhc_pep_{source}_{tstamp}"

            # normalize epitope into {'seq': ...} where possible
            raw_ep = meta.get("epitopes") or meta.get("epitope") or meta.get("epitope_seq") or "UNKNOWN"
            ep_obj = _normalize_epitope(raw_ep, space, region_id)

            # label dict compatible with space.add_label(region, lab)
            lab = {
                "id": mhc_id,
                "coord": meta.get("coord") or (0.0, 0.0),
                "meta": {
                    "type": "MHC_PEPTIDE",
                    # store epitope as a dict {'seq':...}
                    "epitope": ep_obj,
                    "amount": float(meta.get("amount", 1.0)),
                    "origin": source,
                    "created_tick": tstamp
                }
            }

            # write robustly to space
            _robust_add_label(space, region_id, lab)

            events.append({
                "name": "pMHC_created",
                "label_id": mhc_id,
                "coord": lab["coord"],
                "epitope": lab["meta"]["epitope"]
            })

        # -------- activate_tcell: create a TCELL_ACTIVE (or cytokine) label ----
        elif itype == "activate_tcell":
            tstamp = int(time.time())
            source = meta.get("mhc_source") or "mhc_unknown"
            act_id = f"tcell_act_{source}_{tstamp}"

            cytokines = {
                "IL12": float(meta.get("IL12", 0.0)),
                "IFNG": float(meta.get("IFNG", 0.0))
            }

            lab = {
                "id": act_id,
                "coord": meta.get("coord") or (0.0, 0.0),
                "meta": {
                    "type": "TCELL_ACTIVE",
                    "state": "activated",
                    "origin": source,
                    "cytokines": cytokines,
                    "created_tick": tstamp
                }
            }

            _robust_add_label(space, region_id, lab)

            events.append({
                "name": "tcell_activated",
                "label_id": act_id,
                "coord": lab["coord"],
                "cytokines": cytokines
            })

        # -------- fallback / unknown intents ---------------------------------
        else:
            events.append({
                "name": "unknown_intent",
                "intent": intent
            })

    return events


__all__ = ["execute_intents"]

