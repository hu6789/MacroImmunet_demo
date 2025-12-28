# test/test_receptor_library.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scan_master.receptor_library import ReceptorLibrary, match_receptors_from_summary_ext
from scan_master.label_names import get_label_meta

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def test_basic_match():
    print("Running receptor_library basic tests...")
    sample = [
        {"ligand":"IL12","mass":0.6,"freq":1},
        {"ligand":"CXCL10","mass":3.0,"freq":2},
        {"ligand":"ANTIGEN_PARTICLE","mass":8.0,"freq":1},
        {"ligand":"MHC_PEPTIDE","mass":1.0,"freq":1},
    ]

    lib = ReceptorLibrary()
    hits = lib.match(sample)
    receptors = {h['receptor'] for h in hits}
    print("Receptor hits:", receptors)

    expect('CXCR3' in receptors, "CXCL10 -> CXCR3 matched")
    expect('IL12R' in receptors, "IL12 -> IL12R matched")
    expect('TCR' in receptors, "MHC_PEPTIDE -> TCR matched")
    # antigen particle should map to ACE2/entry receptor via registry (may be present)
    expect(any(h['ligand']=='ANTIGEN_PARTICLE' for h in hits) or any(h['receptor'] in ('ACE2','ACE2R') for h in hits),
           "ANTIGEN_PARTICLE mapping (ACE2 or ligand present)")

def test_type_filtering():
    print("Running receptor_library type-filtering tests...")
    sample = [
        {"ligand":"IL12","mass":0.6,"freq":1},
        {"ligand":"CXCL10","mass":2.0,"freq":1},
        {"ligand":"MHC_PEPTIDE","mass":1.0,"freq":1},
    ]
    # require only 'field' ligands (IL12,CXCL10 are fields; MHC_PEPTIDE is surface)
    hits_field_only = match_receptors_from_summary_ext(sample, require_type_match=True, accepted_label_types=['field'])
    ligs = {h['ligand'] for h in hits_field_only}
    expect('IL12' in ligs and 'CXCL10' in ligs, "field-only matches include cytokines")
    expect('MHC_PEPTIDE' not in ligs, "field-only filter excludes surface MHC_PEPTIDE")

def run_all():
    test_basic_match()
    test_type_filtering()
    print("All receptor_library tests passed.")

if __name__ == "__main__":
    run_all()

