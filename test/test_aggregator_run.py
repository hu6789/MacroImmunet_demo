# test/test_aggregator_run.py (robust imports, uses module namespace)
import sys, os
# ensure project root is importable (so scan_master package is found)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import scan_master.label_names as label_names
from scan_master.aggregator import LabelAggregator

def smoke_test():
    print("=== LABEL REGISTRY SAMPLE ===")
    # use module namespace to be robust
    for k in list(label_names.LABEL_REGISTRY.keys())[:8]:
        print(k, "->", label_names.LABEL_REGISTRY[k]['type'])

    # example raw labels as might come from spatial
    raw_labels = [
        {"name": "S_RBD", "mass": 10.0, "created_tick": 10},
        {"name": "virus_particle", "mass": 5.0, "created_tick": 11},
        {"name": "mhc_i_pep", "mass": 1.0, "created_tick": 9, "owner": "DC_3"},
        {"name": "DAMP_frag", "mass": 2.0, "created_tick": 12, "meta": {"source": "spill"}},
        {"name": "IL-12", "mass": 0.6, "created_tick": 12},
    ]

    print("\n=== CLASSIFICATION EXAMPLES ===")
    for r in raw_labels:
        c = label_names.classify_label_item(r)
        print(f"{r['name']:15} -> {c['canonical']:15}  type={c['meta']['type']:8}")

    # test aggregator
    agg = LabelAggregator({"young_thresh": 3, "recent_spill_window": 5})
    ligand_summary = agg.aggregate_labels(raw_labels)
    spectrum = agg.get_spectrum(raw_labels, current_tick=13)

    print("\n=== LIGAND SUMMARY ===")
    for item in ligand_summary:
        print(item)

    print("\n=== SPECTRUM ===")
    for k, v in spectrum.items():
        print(f"{k:20}: {v}")

    # basic assertions
    assert any(item['ligand'] == 'ANTIGEN_PARTICLE' for item in ligand_summary), "ANTIGEN_PARTICLE missing"
    assert spectrum['total_mass'] > 0, "total_mass should be > 0"
    assert spectrum['dominant_epitope'] is not None, "dominant_epitope should exist"

    print("\nSMOKE TEST PASSED.")

if __name__ == "__main__":
    smoke_test()
