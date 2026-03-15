# behaviors_impl/present.py
"""
Present behavior implementation (present_v1).

- Reads cell.captured_antigens (list of antigen dicts).
- For each antigen, extract candidate epitopes:
    - if antigen has 'epitopes' (list of dict with id/seq) use them
    - elif antigen has 'sequence' use naive sliding k-mer extractor (k from params.kmer_k)
    - else skip
- Limit per-antigen by params.max_epitopes_per_antigen.
- Optionally deduplicate across cell.present_list by peptide sequence.
- Append canonical pMHC records to cell.present_list: {pMHC_id, peptide_id (sequence), epitope_seq, mhc_type, presenter}
- Clear captured_antigens after processing.
- Emit env.emit_event("pMHC_presented", payload)
"""
from typing import Any, Dict, List
import itertools
import uuid

def _sliding_kmers(seq: str, k: int):
    if not seq or k <= 0 or len(seq) < k:
        return []
    return [seq[i:i+k] for i in range(0, len(seq)-k+1)]

def present_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    p = payload or {}
    # resolve runtime params (allow payload override)
    max_epitopes = int(params.get("max_epitopes_per_antigen", 3))
    k = int(params.get("kmer_k", 9))
    mhc_types = params.get("mhc_types", ["MHC_I", "MHC_II"])
    dedup = bool(params.get("deduplicate_epitopes", True))
    allow_multi = bool(params.get("allow_multiple_mhc_per_epitope", False))

    captured = list(getattr(cell, "captured_antigens", []) or [])
    if not captured:
        return []

    present_list = getattr(cell, "present_list", None)
    if present_list is None:
        cell.present_list = []
        present_list = cell.present_list

    # build existing peptide sequence set for dedup
    existing_pep_seqs = set()
    if dedup:
        for entry in present_list:
            # prefer canonical peptide sequence field
            seq = entry.get("peptide_id") or entry.get("epitope_seq")
            if seq:
                existing_pep_seqs.add(seq)

    new_entries = []
    for antigen in captured:
        candidates = []
        # if antigen gives explicit epitopes
        if isinstance(antigen.get("epitopes"), list) and antigen.get("epitopes"):
            for e in antigen.get("epitopes"):
                # prefer the epitope sequence as the canonical peptide id (tests expect sequence)
                seq = None
                if isinstance(e, dict):
                    seq = e.get("seq") or e.get("sequence") or e.get("epitope_seq")
                else:
                    seq = str(e)
                if seq:
                    candidates.append({"peptide_seq": seq, "epitope_seq": seq})
        elif antigen.get("sequence"):
            seq_full = antigen.get("sequence")
            kmers = _sliding_kmers(seq_full, k)
            for km in kmers:
                candidates.append({"peptide_seq": km, "epitope_seq": km})
        else:
            # try antigen.epitope_list alias
            if isinstance(antigen.get("epitope_list"), list):
                for e in antigen.get("epitope_list"):
                    if isinstance(e, dict):
                        seq = e.get("seq") or e.get("sequence") or e.get("epitope_seq")
                    else:
                        seq = str(e)
                    if seq:
                        candidates.append({"peptide_seq": seq, "epitope_seq": seq})

        # clip to max_per_antigen (simple head selection; could be randomized)
        candidates = candidates[:max_epitopes]

        for cand in candidates:
            seq = cand.get("peptide_seq")
            epseq = cand.get("epitope_seq", seq)
            if dedup and seq in existing_pep_seqs:
                continue
            # decide mhc type(s) to present on
            mhc_assignments = [mhc_types[0]] if not allow_multi else list(mhc_types)
            for mhc in mhc_assignments:
                entry = {
                    "pMHC_id": str(uuid.uuid4()),
                    "peptide_id": seq,          # canonical peptide sequence
                    "epitope_seq": epseq,
                    "mhc_type": mhc,
                    "presenter": getattr(cell, "id", None),
                    "duration": int(params.get("presentation_duration_ticks", 240))
                }
                present_list.append(entry)
                new_entries.append(entry)
                if dedup:
                    existing_pep_seqs.add(seq)
                if not allow_multi:
                    break

    # clear captured_antigens (best-effort)
    try:
        cell.captured_antigens = []
    except Exception:
        pass

    # emit event
    try:
        if hasattr(env, "emit_event"):
            payload_out = {"presenter": getattr(cell, "id", None), "count": len(new_entries), "tick": getattr(env, "tick", None)}
            env.emit_event("pMHC_presented", payload_out)
    except Exception:
        pass

    # return actions list for test compatibility
    actions = []
    if new_entries:
        actions.append({"name": "pMHC_presented", "payload": {"presenter": getattr(cell, "id", None), "count": len(new_entries)}})
    return actions

