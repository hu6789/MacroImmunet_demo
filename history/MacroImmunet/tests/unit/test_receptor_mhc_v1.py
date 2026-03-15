# tests/unit/test_receptor_mhc_v1.py
import importlib
importlib.invalidate_caches()

from behaviors_impl import mhc

def test_present_mhc_i_basic():
    rec = mhc.present_mhc_i('KQNTLQKYG', peptide_id='S_toy_I_A')
    assert isinstance(rec, dict)
    assert rec.get("mhc_type") == "MHC_I"
    assert 0.0 <= rec.get("affinity", 0.0) <= 1.0
    assert rec.get("peptide_id") == "S_toy_I_A"

def test_present_mhc_ii_basic():
    rec = mhc.present_mhc_ii('ALSYIFCLVFADYKD', peptide_id='S_toy_II_A')
    assert isinstance(rec, dict)
    assert rec.get("mhc_type") == "MHC_II"
    assert 0.0 <= rec.get("affinity", 0.0) <= 1.0
    assert rec.get("peptide_id") == "S_toy_II_A"

