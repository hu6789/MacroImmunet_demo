# test/test_claims.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from scan_master.space import Space

# local mk_label for tests (keeps same shape as other tests)
def mk_label(name, mass=1.0, created_tick=0, coord=None, owner=None, meta=None, id=None):
    return {
        "id": id,
        "name": name,
        "mass": mass,
        "created_tick": created_tick,
        "coord": coord,
        "owner": owner,
        "meta": meta or {},
    }

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def test_claim_basic():
    s = Space()
    r = "claim_r"
    # add one antigen label
    s.add_label(r, mk_label("ANTIGEN_PARTICLE", mass=5.0, created_tick=0))
    labels = s.get_labels(r)
    expect(len(labels) == 1, "seed label present")
    lid = labels[0]["id"]

    # first claimant claims successfully
    ok = s.claim_label(r, lid, "DC_1")
    expect(ok, "claim succeeded first")

    found = s.find_label(r, lid)
    expect(found is not None and found.get("owner") == "DC_1", "owner recorded after claim")

    # second claimant fails to claim same label
    ok2 = s.claim_label(r, lid, "DC_2")
    expect(not ok2, "second claim failed (already owned)")

    # transfer (force) to another owner should succeed (transfer overwrites)
    t = s.transfer_label(r, lid, "DC_2")
    expect(t, "transfer succeeded")
    found2 = s.find_label(r, lid)
    expect(found2 is not None and found2.get("owner") == "DC_2", "owner updated after transfer")

    # remove label
    okr = s.remove_label(r, lid)
    expect(okr, "remove label succeeded")
    expect(s.find_label(r, lid) is None, "label gone after remove")

def test_claim_nonexistent():
    s = Space()
    r = "claim_r2"
    # claim a non-existent id
    ok = s.claim_label(r, "no-such-id", "DC")
    expect(not ok, "claim on non-existent label returns False")

def test_multiple_labels_and_claims():
    s = Space()
    r = "claim_r3"
    # add multiple antigen labels
    s.add_label(r, mk_label("ANTIGEN_PARTICLE", mass=3.0, created_tick=0))
    s.add_label(r, mk_label("ANTIGEN_PARTICLE", mass=4.0, created_tick=1))
    all_labels = s.get_labels(r)
    expect(len(all_labels) == 2, "two labels seeded")
    ids = [l["id"] for l in all_labels]

    # different claimants take different labels
    ok1 = s.claim_label(r, ids[0], "DC_A")
    ok2 = s.claim_label(r, ids[1], "DC_B")
    expect(ok1 and ok2, "both labels claimed by different DCs")

    # owners are independent
    f0 = s.find_label(r, ids[0])
    f1 = s.find_label(r, ids[1])
    expect(f0.get("owner") == "DC_A" and f1.get("owner") == "DC_B", "owners set correctly for separate labels")

def test_transfer_overwrites_existing_claim():
    s = Space()
    r = "claim_r4"
    s.add_label(r, mk_label("ANTIGEN_PARTICLE", mass=2.0, created_tick=0))
    lid = s.get_labels(r)[0]["id"]

    # claim by initial owner
    ok = s.claim_label(r, lid, "DC_orig")
    expect(ok, "initial claim ok")
    f = s.find_label(r, lid)
    expect(f.get("owner") == "DC_orig", "owner recorded")

    # transfer should overwrite even if previously owned
    ok_tr = s.transfer_label(r, lid, "DC_new")
    expect(ok_tr, "transfer api returns True")
    f2 = s.find_label(r, lid)
    expect(f2.get("owner") == "DC_new", "owner overwritten by transfer")

def test_atomic_like_sequence():
    """
    Simulate two quick attempts to claim the same label sequentially:
    first should succeed, second should fail — ensures claim is stateful/atomic at API level.
    """
    s = Space()
    r = "claim_r5"
    s.add_label(r, mk_label("ANTIGEN_PARTICLE", mass=1.0, created_tick=0))
    lid = s.get_labels(r)[0]["id"]

    # claimant 1
    ok1 = s.claim_label(r, lid, "DC1")
    # immediately claimant 2 tries
    ok2 = s.claim_label(r, lid, "DC2")
    expect(ok1 and (not ok2), "sequential claims: first wins, second loses")

def run_all():
    print("Running claim/ownership tests...")
    test_claim_basic()
    test_claim_nonexistent()
    test_multiple_labels_and_claims()
    test_transfer_overwrites_existing_claim()
    test_atomic_like_sequence()
    print("All claim tests passed.")

if __name__ == "__main__":
    run_all()

