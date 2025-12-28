# test/test_selector.py
import sys, os, math
sys.path.append(os.path.abspath("."))

print("Importing selector...")
from cell_master import selector
from scan_master.space import Space
import random

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def make_label(name, coord=None, meta=None, owner=None):
    lab = {"id": name, "name": name, "coord": coord, "meta": meta or {}, "owner": owner}
    return lab

def test_basic_selection_and_type_filter():
    s = Space()
    s.ensure_region("r0")
    s.add_label("r0", make_label("DC", coord=(0,0)))
    s.add_label("r0", make_label("NAIVE_T", coord=(5,5)))
    # by type
    got = selector.select_candidates(s, "r0", cell_type="DC")
    expect(len(got)==1 and got[0]["name"]=="DC", "select by canonical/type")

def test_radius_selection_uses_space_method():
    s = Space()
    s.ensure_region("r")
    s.add_label("r", make_label("A", coord=(0,0)))
    s.add_label("r", make_label("B", coord=(3,4)))  # distance 5
    s.add_label("r", make_label("C", coord=(10,10)))
    got = selector.select_candidates(s, "r", coord=(0,0), radius=5.0)
    # A and B are in radius; order may vary
    names = set([g["name"] for g in got])
    expect(names == {"A","B"}, "radius selection returned expected set")

def test_bbox_and_owner_and_capacity_filters():
    s = Space()
    s.ensure_region("r1")
    s.add_label("r1", make_label("DC", coord=(1,1), meta={"capacity":5}, owner="DC1"))
    s.add_label("r1", make_label("DC", coord=(20,20), meta={"capacity":0.5}, owner="DC2"))
    # bbox
    bbox = (0,0,5,5)
    got = selector.select_candidates(s, "r1", bbox=bbox, cell_type="DC")
    expect(len(got)==1 and got[0]["owner"]=="DC1", "bbox + type filters")
    # capacity filter
    got2 = selector.select_candidates(s, "r1", cell_type="DC", min_capacity=1.0, capacity_key="capacity")
    expect(len(got2)==1 and got2[0]["owner"]=="DC1", "min_capacity filters correctly")
    # owner filter
    got3 = selector.select_candidates(s, "r1", cell_type="DC", owner="DC2")
    expect(len(got3)==1 and got3[0]["owner"]=="DC2", "owner filter works")

def test_sampling_fraction_and_count_deterministic():
    s = Space()
    s.ensure_region("r2")
    for i in range(10):
        s.add_label("r2", make_label(f"C{i}", coord=(i,i)))
    # deterministic seed
    rng1 = random.Random(42)
    a = selector.select_candidates(s, "r2", sample_fraction=0.5, rng=rng1)
    rng2 = random.Random(42)
    b = selector.select_candidates(s, "r2", sample_fraction=0.5, rng=rng2)
    # same selection when same seed
    ids_a = sorted([x["id"] for x in a])
    ids_b = sorted([x["id"] for x in b])
    expect(ids_a == ids_b, "deterministic sampling with same seed")

    # sample_count absolute
    c = selector.select_candidates(s, "r2", sample_count=3, rng=123)
    expect(len(c)==3, "sample_count honored")

def test_max_select_and_edge_cases():
    s = Space()
    s.ensure_region("rx")
    s.add_label("rx", make_label("X1"))
    s.add_label("rx", make_label("X2"))
    # fraction >1 treated as count
    got = selector.select_candidates(s, "rx", sample_fraction=5)
    expect(len(got) == 2, "fraction>1 clamps to available count")
    # max_select caps
    got2 = selector.select_candidates(s, "rx", sample_fraction=1.0, max_select=1)
    expect(len(got2) == 1, "max_select caps result")

def run_all():
    test_basic_selection_and_type_filter()
    test_radius_selection_uses_space_method()
    test_bbox_and_owner_and_capacity_filters()
    test_sampling_fraction_and_count_deterministic()
    test_max_select_and_edge_cases()
    print("\nAll selector tests passed.")

if __name__ == "__main__":
    run_all()

