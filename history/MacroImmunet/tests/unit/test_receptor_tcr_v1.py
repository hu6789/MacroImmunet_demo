# tests/unit/test_receptor_tcr_v1.py
import importlib
importlib.invalidate_caches()

from behaviors_impl import tcr, mhc

def test_generate_repertoire_and_affinity_range():
    rep = tcr.generate_simple_repertoire(seed=42, size=5, kmer_k=9)
    assert isinstance(rep, list)
    assert len(rep) == 5
    # pick a pmhc and compute affinity across repertoire
    pmhc = mhc.present_mhc_i("KQNTLQKYG", peptide_id="S_toy_I_A")
    affs = [tcr.compute_affinity(c, pmhc) for c in rep]
    for a in affs:
        assert 0.0 <= a <= 1.0

def test_specificity_boost():
    rep = tcr.generate_simple_repertoire(seed=2025, size=20, kmer_k=9)
    # ensure there's at least one clone with specificity to S_toy_I_A by generator logic
    has_spec = any(("S_toy_I_A" in c.get("specificity", set())) for c in rep)
    assert has_spec
    pmhc = mhc.present_mhc_i("KQNTLQKYG", peptide_id="S_toy_I_A")
    # find best affinity clone
    best = max(rep, key=lambda c: tcr.compute_affinity(c, pmhc))
    best_aff = tcr.compute_affinity(best, pmhc)
    assert best_aff >= 0.7  # specificity path yields high affinity

