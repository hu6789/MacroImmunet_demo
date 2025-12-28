# test/test_owner_utils.py
import sys, os, importlib
sys.path.append(os.path.abspath("."))

from cell_master.owner_utils import OwnerUtils

class FakeSpace:
    def __init__(self):
        # labels keyed by id
        self._labels = {
            "L1": {"id":"L1","coord":(0,0),"owner":None},
            "L2": {"id":"L2","coord":(1,1),"owner":None},
        }
    def get_label(self, lid):
        return self._labels.get(lid)
    def claim_label(self, lid, owner):
        l = self._labels.get(lid)
        if not l:
            return False
        if l.get("owner"):
            return False
        l["owner"] = owner
        return True
    def transfer_label(self, lid, new_owner, force=False):
        l = self._labels.get(lid)
        if not l:
            return False
        if l.get("owner") and not force:
            return False
        l["owner"] = new_owner
        return True
    def release_label(self, lid, owner=None):
        l = self._labels.get(lid)
        if not l:
            return False
        if owner is not None and l.get("owner") != owner:
            return False
        l["owner"] = None
        return True

class FakeFeedback:
    # simple passthrough to space in tests
    def __init__(self, space):
        self.space = space
    def claim_label(self, lid, owner):
        return self.space.claim_label(lid, owner)
    def transfer_label(self, lid, owner, force=False):
        return self.space.transfer_label(lid, owner, force=force)
    def release_label(self, lid, owner=None):
        return self.space.release_label(lid, owner)

def expect(ok, msg):
    if ok:
        print("[OK]", msg)
    else:
        print("[FAIL]", msg)
        raise AssertionError(msg)

def run_tests():
    sp = FakeSpace()
    fb = FakeFeedback(sp)
    ou = OwnerUtils(sp, feedback=fb, verbose=False)

    # claim success
    r = ou.claim("L1", "A")
    expect(r["ok"] is True and r["new_owner"] == "A", "claim L1 by A succeeds")
    # second claim fail
    r2 = ou.claim("L1", "B")
    expect(r2["ok"] is False and r2["prev_owner"] == "A", "second claim fails (owner A)")

    # transfer without force should fail when owned
    r3 = ou.transfer("L1", "C", force=False)
    expect(r3["ok"] is False and r3["prev_owner"] == "A", "transfer without force fails when owned")

    # transfer with force should succeed
    r4 = ou.transfer("L1", "C", force=True)
    expect(r4["ok"] is True and r4["new_owner"] == "C", "transfer with force succeeds")

    # release by wrong owner should fail
    r5 = ou.release("L1", owner_id="A")
    expect(r5["ok"] is False and r5["prev_owner"] == "C", "release by wrong owner fails")

    # release by correct owner succeeds
    r6 = ou.release("L1", owner_id="C")
    expect(r6["ok"] is True and r6["new_owner"] is None, "release by C succeeds")

    # claim L2
    r7 = ou.claim("L2", "X")
    expect(r7["ok"] is True and r7["new_owner"] == "X", "claim L2 by X succeeds")

    print("All OwnerUtils tests passed.")

if __name__ == "__main__":
    run_tests()

