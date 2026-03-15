# behaviors_impl/tcr.py
"""
Simple deterministic TCR repertoire generator and affinity computation for tests.

Exports:
 - generate_simple_repertoire(seed:int, size:int, kmer_k:int) -> list of clonotypes
 - compute_affinity(clonotype, pmhc_entry) -> float in [0..1]

Clonotype format:
 {
   "id": "clonex",
   "specificity": set()   # peptide_ids that clonotype specifically recognizes (may be empty)
   "kmers": set(...)      # k-mers representing CDR-like signature
 }

Affinity:
 - if pmhc.peptide_id in clonotype.specificity -> boosted high affinity (0.85..1.0)
 - else compute k-mer overlap fraction -> map via logistic to [0..0.9]
"""
from typing import List, Dict, Set
import random
import hashlib
import math

def _seeded_random_choices(seed, pool, count):
    rnd = random.Random(seed)
    return [rnd.choice(pool) for _ in range(count)]

def _deterministic_kmers_from_peptide(peptide_seq: str, k: int):
    kmers = set()
    if peptide_seq is None:
        return kmers
    for i in range(max(0, len(peptide_seq) - k + 1)):
        kmers.add(peptide_seq[i:i+k])
    # if too few, add hashed-derived pseudo-kmers
    if not kmers:
        h = hashlib.sha256(peptide_seq.encode()).hexdigest()
        # split hex into pseudo kmers of length k
        for i in range(0, min(5, len(h)-k+1)):
            kmers.add(h[i:i+k])
    return kmers

def generate_simple_repertoire(seed:int=2025, size:int=20, kmer_k:int=9) -> List[Dict]:
    rng = random.Random(seed)
    repertoire = []
    # generate some specificities deterministically for tests
    for i in range(size):
        # create a pseudo-kmer signature
        base = f"clone_{seed}_{i}"
        # produce kmers from the base hashed string
        hashed = hashlib.sha256(base.encode()).hexdigest()
        # create kmers by sliding over hex (turn hex to letters may be fine)
        kmers = set()
        # convert hashed to an ASCII-like string by taking pairs -> letters
        ascii_like = "".join(chr((int(hashed[j:j+2], 16) % 26) + 65) for j in range(0, min(len(hashed), 26), 2))
        for j in range(max(0, len(ascii_like) - kmer_k + 1)):
            kmers.add(ascii_like[j:j+kmer_k])
        # add fallback if empty
        if not kmers:
            kmers = {"X"*kmer_k}
        # deterministic specificity: some clones target named peptide ids
        specificity = set()
        if i % 7 == 0:
            specificity.add("S_toy_I_A")
        if i % 11 == 0:
            specificity.add("S_toy_II_A")
        repertoire.append({"id": f"clone_{i}", "specificity": specificity, "kmers": kmers})
    return repertoire

def _sigmoid(x, k=8, x0=0.5):
    return 1.0 / (1.0 + math.exp(-k*(x - x0)))

def compute_affinity(clonotype: Dict, pmhc_entry: Dict) -> float:
    # if explicit specificity, high affinity path
    pid = pmhc_entry.get("peptide_id") or pmhc_entry.get("seq")
    if pid and pid in (clonotype.get("specificity") or set()):
        # deterministic boosted affinity based on id hash
        h = int(hashlib.sha256(pid.encode()).hexdigest()[:8], 16) % 1000
        return 0.85 + (h / 1000.0) * 0.15  # 0.85..1.0
    # else compute k-mer overlap between clonotype.kmers and pmhc seq kmers
    seq = pmhc_entry.get("seq") or ""
    k = next(iter(clonotype.get("kmers") or {"X"}))
    klen = len(k)
    pmhc_kmers = set()
    for i in range(max(0, len(seq) - klen + 1)):
        pmhc_kmers.add(seq[i:i+klen])
    if not pmhc_kmers:
        return 0.0
    kmers = clonotype.get("kmers") or set()
    overlap = len(kmers & pmhc_kmers)
    frac = overlap / float(max(1, len(kmers | pmhc_kmers)))
    # map fraction to affinity via sigmoid and scale to 0..0.85
    aff = _sigmoid(frac, k=12, x0=0.15) * 0.85
    return float(max(0.0, min(1.0, aff)))

