# FILE: cell_master/tcell_activation.py
"""
Simple T-cell activation & differentiation helper for the demo Step4.

This module provides a compact, compatibility-focused function:

    activate_tcells(space, region_id, rng=None, params=None)

Behaviour (minimal, deterministic-ish):
 - Scans `space` for `MHC_PEPTIDE` labels in `region_id` (via space.get_labels)
 - Scans `space` for `NAIVE_T` cell labels in the same region
 - For each naive T it attempts pMHC recognition: if a peptide epitope seq exists,
   recognition happens with a small probabilistic match (can be tuned).
 - If recognized, it writes an activation label and a differentiation label:
     - If local IL12 (from field labels) >= params['il12_thresh'] -> produce TH1 label
     - else -> produce CTL label
 - The function returns a list of events written.

Compatibility notes: the function attempts multiple ways to write labels to `space`:
 - space.add_label(region, lab)  OR  space.add_label(lab, region)  OR  space.add_label(lab)
 - fallback to space._local_labels (dict keyed by region or list) or space.labels list

The goal is to be minimally invasive and testable in the existing demo.
"""
from typing import Any, Dict, List, Optional
import time
import random
import copy


def _write_label_to_space(space: Any, lab: Dict[str, Any], region_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Robust label writer used by demo utilities."""
    try:
        # 1) add_label(region, lab)
        if region_id and hasattr(space, 'add_label') and callable(space.add_label):
            try:
                res = space.add_label(region_id, lab)
                return lab
            except Exception:
                pass
        # 2) add_label(lab, region)
        if region_id and hasattr(space, 'add_label') and callable(space.add_label):
            try:
                res = space.add_label(lab, region_id)
                return lab
            except Exception:
                pass
        # 3) add_label(lab)
        if hasattr(space, 'add_label') and callable(space.add_label):
            try:
                res = space.add_label(lab)
                return lab
            except Exception:
                pass
        # 4) _local_labels
        if hasattr(space, '_local_labels'):
            try:
                ll = getattr(space, '_local_labels')
                if isinstance(ll, dict) and region_id is not None:
                    lst = ll.setdefault(region_id, [])
                    # replace existing
                    for i, e in enumerate(list(lst)):
                        if isinstance(e, dict) and e.get('id') == lab.get('id'):
                            lst[i] = lab
                            break
                    else:
                        lst.append(lab)
                    return lab
                if isinstance(ll, list):
                    for i, e in enumerate(list(ll)):
                        if isinstance(e, dict) and e.get('id') == lab.get('id'):
                            ll[i] = lab
                            break
                    else:
                        ll.append(lab)
                    return lab
            except Exception:
                pass
        # 5) space.labels list
        if hasattr(space, 'labels'):
            try:
                labs = getattr(space, 'labels') or []
                if isinstance(labs, list):
                    for i, e in enumerate(list(labs)):
                        if isinstance(e, dict) and e.get('id') == lab.get('id'):
                            labs[i] = lab
                            break
                    else:
                        labs.append(lab)
                    return lab
            except Exception:
                pass
    except Exception:
        pass
    return None


def _get_labels(space: Any, region_id: Optional[str] = None) -> List[Dict[str, Any]]:
    fn = getattr(space, 'get_labels', None)
    if callable(fn):
        try:
            return fn(region_id) or []
        except Exception:
            pass
    # fallback to lists
    if hasattr(space, '_local_labels'):
        ll = getattr(space, '_local_labels')
        if isinstance(ll, dict) and region_id is not None:
            return ll.get(region_id, []) or []
        if isinstance(ll, list):
            return ll
    if hasattr(space, 'labels') and getattr(space, 'labels') is not None:
        return getattr(space, 'labels')
    return []


def _get_field_value(labels: List[Dict[str, Any]], field_name: str) -> float:
    # simple aggregator: return sum of 'amount' for labels whose meta.type == field_name
    total = 0.0
    for l in labels:
        try:
            mt = (l.get('meta') or {}).get('type')
            if mt == field_name:
                total += float((l.get('meta') or {}).get('amount', 0.0) or 0.0)
        except Exception:
            continue
    return total


def activate_tcells(space: Any, region_id: str, rng: Optional[random.Random] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Activate naive T cells from pMHC labels and produce differentiation labels.

    Returns list of event dicts describing activations/differentiations.
    """
    rng = rng or random.Random()
    p = dict(params or {})
    il12_thresh = float(p.get('il12_thresh', 0.5))
    recognition_prob = float(p.get('recognition_prob', 0.8))

    events: List[Dict[str, Any]] = []

    labels = _get_labels(space, region_id)
    # collect pMHCs
    pmhcs = [l for l in labels if (l.get('meta') or {}).get('type') == 'MHC_PEPTIDE']
    if not pmhcs:
        return events

    # collect naive T cells (labels with meta.type == 'NAIVE_T' or name/type fields)
    naive_ts = []
    for l in labels:
        m = (l.get('meta') or {}).get('type')
        if m == 'NAIVE_T' or l.get('type') == 'NAIVE_T' or l.get('name') == 'NAIVE_T':
            naive_ts.append(l)

    # compute local IL12 field from labels as simple proxy
    il12_local = _get_field_value(labels, 'IL12')

    # for each naive T, try to recognize any pMHC
    for tcell in naive_ts:
        tid = tcell.get('id') or tcell.get('name') or f"naive_{int(time.time())}"
        for pmhc in pmhcs:
            epitope = (pmhc.get('meta') or {}).get('epitope') or (pmhc.get('meta') or {}).get('epitopes')
            # normalize epitope to a seq string for matching
            seq = None
            try:
                if isinstance(epitope, list) and epitope:
                    seq = epitope[0].get('seq') if isinstance(epitope[0], dict) else str(epitope[0])
                elif isinstance(epitope, dict):
                    seq = epitope.get('seq')
                elif isinstance(epitope, str):
                    seq = epitope
            except Exception:
                seq = None

            # if no sequence, assume a generic match possibility
            prob = recognition_prob if seq else (recognition_prob * 0.5)
            if rng.random() <= prob:
                # recognized -> create activation label
                activated_id = f"t_activated_{tid}_{int(time.time())}"
                lab_act = {
                    'id': activated_id,
                    'coord': tcell.get('coord', None),
                    'meta': {
                        'type': 'T_CELL_ACTIVATED',
                        'parent': tid,
                        'epitope': seq or 'UNKNOWN',
                        'created_tick': int(time.time()),
                    }
                }
                _write_label_to_space(space, lab_act, region_id=region_id)
                events.append({'name': 'tcell_activated', 'tcell_id': tid, 'epitope': seq, 'label_id': activated_id})

                # differentiation decision
                if il12_local >= il12_thresh:
                    diff_type = 'TH1'
                else:
                    diff_type = 'CTL'

                diff_id = f"t_diff_{tid}_{diff_type}_{int(time.time())}"
                lab_diff = {
                    'id': diff_id,
                    'coord': tcell.get('coord', None),
                    'meta': {
                        'type': diff_type,
                        'parent': tid,
                        'created_tick': int(time.time()),
                    }
                }
                _write_label_to_space(space, lab_diff, region_id=region_id)
                events.append({'name': 'tcell_differentiated', 'tcell_id': tid, 'to': diff_type, 'label_id': diff_id})

                # attach a durable TCR_PERTYPE surface label as well (lightweight)
                tcr_id = f"t_tcr_{tid}_{int(time.time())}"
                lab_tcr = {
                    'id': tcr_id,
                    'coord': tcell.get('coord', None),
                    'meta': {
                        'type': 'TCR_PERTYPE',
                        'parent': tid,
                        'tcr_type': diff_type,
                        'created_tick': int(time.time()),
                    }
                }
                _write_label_to_space(space, lab_tcr, region_id=region_id)
                events.append({'name': 'tcr_assigned', 'tcell_id': tid, 'tcr_label': tcr_id, 'tcr_type': diff_type})

                # a single recognition is sufficient for this tcell this tick
                break
    return events


# End of file

