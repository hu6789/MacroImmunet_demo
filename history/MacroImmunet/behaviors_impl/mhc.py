# behaviors_impl/mhc.py
"""
Simple MHC helpers for unit tests.

Provides:
 - present_mhc_i(peptide_seq, peptide_id=None, mhc_props=None)
 - present_mhc_ii(peptide_seq, peptide_id=None, mhc_props=None)

Return a pMHC-like dict:
 {
   "peptide_id": peptide_id or peptide_seq,
   "seq": peptide_seq,
   "mhc_type": "MHC_I" or "MHC_II",
   "affinity": float  # [0..1]
 }
Affinity is a deterministic heuristic based on length preference and simple hashing.
"""
from typing import Optional, Dict
import math
import hashlib

def _det_hash_to_float(s: str) -> float:
    # deterministic pseudo-random float 0..1 for string s
    h = hashlib.sha256(s.encode("utf8")).digest()
    # use first 8 bytes as integer
    v = int.from_bytes(h[:8], "big")
    return (v % 10**9) / float(10**9)

def _length_pref_score(seq: str, preferred_lengths):
    return 1.0 if len(seq) in preferred_lengths else max(0.0, 1.0 - abs(len(seq) - (preferred_lengths[0])) * 0.1)

def _sigmoid(x, k=10, x0=0.5):
    return 1.0 / (1.0 + math.exp(-k*(x - x0)))

def present_mhc_i(peptide_seq: str, peptide_id: Optional[str]=None, mhc_props: Optional[Dict]=None) -> Dict:
    mhc_props = mhc_props or {"preferred_lengths": [8,9,10,11]}
    base = _det_hash_to_float(peptide_seq + "_I")
    length_score = _length_pref_score(peptide_seq, mhc_props.get("preferred_lengths", [9]))
    # mix base and length into raw score 0..1
    raw = 0.3 * base + 0.7 * length_score
    affinity = _sigmoid(raw, k=8, x0=0.4)
    return {
        "peptide_id": peptide_id or peptide_seq,
        "seq": peptide_seq,
        "mhc_type": "MHC_I",
        "affinity": float(max(0.0, min(1.0, affinity)))
    }

def present_mhc_ii(peptide_seq: str, peptide_id: Optional[str]=None, mhc_props: Optional[Dict]=None) -> Dict:
    mhc_props = mhc_props or {"preferred_lengths": [13,14,15]}
    base = _det_hash_to_float(peptide_seq + "_II")
    length_score = _length_pref_score(peptide_seq, mhc_props.get("preferred_lengths", [15]))
    raw = 0.25 * base + 0.75 * length_score
    affinity = _sigmoid(raw, k=7, x0=0.45)
    return {
        "peptide_id": peptide_id or peptide_seq,
        "seq": peptide_seq,
        "mhc_type": "MHC_II",
        "affinity": float(max(0.0, min(1.0, affinity)))
    }

