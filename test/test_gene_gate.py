# test/test_gene_gate.py
# Simple smoke / unit tests for cell_master.gene_gate
# Usage: PYTHONPATH=. python3 test/test_gene_gate.py

import sys, os, math
sys.path.append(os.path.abspath("."))

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def run_all():
    print("Importing gene_gate...")
    try:
        from cell_master import gene_gate
    except Exception as e:
        print("[FAIL] import cell_master.gene_gate failed:", e)
        raise

    print("Testing evaluate_cell required_genes / forbidden_genes ...")
    class C1:
        def __init__(self):
            # genes map and flat flags both supported
            self.meta = {"genes": {"A": True, "B": False}, "X": True}

    c = C1()
    ok, details = gene_gate.evaluate_cell(c, {"required_genes": ["A"]})
    expect(ok, "required_genes A passes")
    expect(details.get("passed", True) is True, "details.passed True for required")

    ok2, _ = gene_gate.evaluate_cell(c, {"required_genes": ["NONEXIST"]})
    expect(ok2 is False, "missing required gene fails")

    ok3, _ = gene_gate.evaluate_cell(c, {"forbidden_genes": ["X"]})
    expect(ok3 is False, "forbidden gene X fails")

    print("Testing min_expression check ...")
    class C2:
        def __init__(self):
            self.meta = {"expression": {"viral_load": 5.5}, "viral_load": 5.5}
    c2 = C2()
    ok4, det = gene_gate.evaluate_cell(c2, {"min_expression": {"viral_load": 1.0}})
    expect(ok4 is True, "min_expression satisfied (viral_load 5.5 >= 1.0)")
    ok5, _ = gene_gate.evaluate_cell(c2, {"min_expression": {"viral_load": 6.0}})
    expect(ok5 is False, "min_expression fails when too high threshold")

    print("Testing custom_pred callable ...")
    def pred_positive_meta(cell):
        return bool(getattr(cell, "meta", {}).get("viral_load", 0) > 0)
    ok6, _ = gene_gate.evaluate_cell(c2, {"custom_pred": pred_positive_meta})
    expect(ok6 is True, "custom_pred True when viral_load > 0")
    ok7, _ = gene_gate.evaluate_cell(c2, {"custom_pred": lambda cc: False})
    expect(ok7 is False, "custom_pred False respected")

    print("Testing batch_filter ...")
    cells = [C2() for _ in range(6)]
    filtered = gene_gate.batch_filter(cells, {"min_expression": {"viral_load": 1.0}})
    expect(len(filtered) == 6, "batch_filter keeps all that pass")
    filtered2 = gene_gate.batch_filter(cells, {"min_expression": {"viral_load": 10.0}})
    expect(len(filtered2) == 0, "batch_filter excludes those that don't pass")

    print("Testing sample_fraction deterministic behavior with seed ...")
    import random
    gg = gene_gate.GeneGate(seed=12345)
    items = list(range(100))
    # sample approx 20%
    sel1 = gg.sample_fraction(items, fraction=0.2, rng=random.Random(42))
    sel2 = gg.sample_fraction(items, fraction=0.2, rng=random.Random(42))
    expect(sel1 == sel2, "sampling deterministic with same RNG seed")

    # fraction > 1 interpreted as absolute count
    sel3 = gg.sample_fraction(items, fraction=5.0, rng=random.Random(7))
    expect(len(sel3) == 5, "fraction >1 treated as count (rounded)")

    # fraction==1 keeps all (but apply max_select cap)
    sel_all = gg.sample_fraction(items, fraction=1.0, max_select=10, rng=random.Random(1))
    expect(len(sel_all) == 10, "fraction=1 with max_select caps at max_select")

    # small population: non-zero fraction should possibly return empty (allowed)
    small = [1,2,3]
    sel_small = gg.sample_fraction(small, fraction=0.01, rng=random.Random(123))
    expect(isinstance(sel_small, list), "sample_fraction returns list even if empty")

    print("Edge-case: empty candidates -> empty result")
    empty = gg.sample_fraction([], fraction=0.5)
    expect(empty == [], "sample_fraction([]) -> []")

    print("\nAll gene_gate tests passed.")

if __name__ == "__main__":
    run_all()

