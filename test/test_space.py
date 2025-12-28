# test/test_space.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from scan_master.space import Space
# --- override mk_label for tests (more flexible) ---
def mk_label(name, mass=1.0, created_tick=0, coord=None, owner=None, meta=None, id=None):
    """
    Flexible test label generator.
    Tests need to specify coord/owner/meta, so we override the utils.mk_label.
    """
    return {
        "id": id,               # None -> Space will assign UUID
        "name": name,
        "mass": mass,
        "created_tick": created_tick,
        "coord": coord,         # optional (x,y)
        "owner": owner,         # optional owner id
        "meta": meta or {},     # metadata
    }
# -----------------------------------------------


def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def test_basic_ops():
    s = Space()
    r = "r0"
    l1 = mk_label("A", mass=1.0, created_tick=0)
    s.add_label(r, l1)
    got = s.get_labels(r)
    expect(len(got) == 1 and got[0]["name"] == "A", "add/get basic")

    s.extend_labels(r, [mk_label("B", mass=2.0, created_tick=1, coord=(2.0,3.0))])
    got2 = s.get_labels(r)
    expect(len(got2) == 2, "extend_labels")

    # spatial query
    found = s.get_labels_in_radius(r, center=(2.0,3.0), radius=0.1)
    expect(len(found) == 1 and found[0]["name"] == "B", "get_labels_in_radius")

    # pop
    popped = s.pop_labels(r)
    expect(len(popped) == 2, "pop_labels content")
    expect(len(s.get_labels(r)) == 0, "pop cleared")

def test_claim_transfer_remove():
    s = Space()
    r = "r1"
    lab = mk_label("ANTIGEN", mass=5.0, created_tick=0)
    s.add_label(r, lab)
    labels = s.get_labels(r)
    lid = labels[0]["id"]
    ok = s.claim_label(r, lid, "DC_1")
    expect(ok, "claim succeeded first")
    ok2 = s.claim_label(r, lid, "DC_2")
    expect(not ok2, "second claim failed")
    # transfer
    okt = s.transfer_label(r, lid, "DC_2")
    expect(okt, "transfer succeeded")
    found = s.find_label(r, lid)
    expect(found.get("owner") == "DC_2", "owner updated")
    # remove
    okr = s.remove_label(r, lid)
    expect(okr, "remove label succeeded")
    expect(s.find_label(r, lid) is None, "label gone")

def test_hotspot_registry_and_summary():
    s = Space()
    r = "region_hot"
    # seed IL12, antigen, damp
    s.add_label(r, mk_label("S_RBD", mass=8.0, created_tick=0, coord=(1,1)))
    s.add_label(r, mk_label("S_RBD", mass=4.0, created_tick=1, coord=(1.5,1.2)))
    s.add_label(r, mk_label("DAMP_frag", mass=1.0, created_tick=1))
    # add hotspot record
    hid = s.add_hotspot(r, center=(1.2,1.1), created_tick=2, meta={"reason":"test"})
    hs = s.get_hotspots(r)
    expect(len(hs) == 1 and hs[0]["hotspot_id"] == hid, "hotspot registered")
    # summary
    out = s.summarize_region(r, current_tick=3)
    ligand = {i["ligand"]:i["mass"] for i in out["ligand_summary"]}
    expect("ANTIGEN_PARTICLE" in ligand and ligand["ANTIGEN_PARTICLE"] >= 12.0, "ANTIGEN mass aggregated")
    expect(out["spectrum"]["num_damp"] >= 1, "num_damp detected")
    # has_recent_label
    ok_recent = s.has_recent_label(r, "DAMP_frag", cooldown_ticks=5, current_tick=3)
    expect(ok_recent, "has_recent_label true for recent DAMP")

def run_all():
    print("Running space tests...")
    test_basic_ops()
    test_claim_transfer_remove()
    test_hotspot_registry_and_summary()
    print("All space tests passed.")

if __name__ == "__main__":
    run_all()

