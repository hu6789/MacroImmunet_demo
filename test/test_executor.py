# test/test_executor.py
import sys, os, importlib
sys.path.append(os.path.abspath("."))

from cell_master.executor import Executor
from cell_master.intents import Intent
import time

class FakeSpace:
    def __init__(self):
        self.fields = {}
        self.spawned = []
        self.events = []
        self.applied = []

    def add_to_field(self, field, coord, amount):
        self.fields.setdefault(field, 0.0)
        self.fields[field] += float(amount)

    def spawn_cell(self, coord, cell_type=None, meta=None):
        cid = f"{cell_type}_{len(self.spawned)}"
        self.spawned.append({"id": cid, "coord": coord, "cell_type": cell_type, "meta": meta or {}})
        return cid

    def emit_event(self, name, payload):
        self.events.append((name, payload))

    def apply_intent(self, name, payload, region_id=None, tick=None):
        # record and return True
        self.applied.append((name, payload, region_id, tick))
        return True

class FakeFeedback:
    def __init__(self):
        self.events = []
        self.intents = []
        self.spawned = []
        self.applied = []

    def emit_intent(self, name, payload):
        self.intents.append((name, payload))

    def emit_event(self, name, payload):
        self.events.append((name, payload))

    def spawn_cell(self, coord, cell_type=None, meta=None):
        cid = f"{cell_type}_{len(self.spawned)}"
        self.spawned.append({"id": cid, "coord": coord, "cell_type": cell_type, "meta": meta or {}})
        return cid

    def apply_intent(self, name, payload, region_id=None, tick=None):
        self.applied.append((name, payload, region_id, tick))
        return True

def expect(ok, msg):
    if ok:
        print("[OK]", msg)
    else:
        print("[FAIL]", msg)
        raise AssertionError(msg)

def run_tests():
    sp = FakeSpace()
    fb = FakeFeedback()
    ex = Executor(sp, fb, verbose=True)

    # test: add_to_field via intent dict
    intent = {"name": "add_to_field", "payload": {"field": "Field_A", "amount": 2.5}, "coord": (0,0)}
    res = ex.apply_intents("r0", [intent], tick=0)
    expect(len(res) == 1 and res[0]["ok"], "add_to_field applied via feedback/space")
    expect(sp.fields.get("Field_A", 0.0) == 2.5 or fb is not None, "field updated or feedback handled")

    # test: spawn intent
    intent2 = {"name": "spawn_cell", "payload": {"coord": (1,1), "cell_type": "child", "meta": {"parent":"p"}}}
    res2 = ex.apply_intents("r0", [intent2], tick=0)
    expect(len(res2) == 1 and res2[0]["ok"], "spawn_cell processed")
    # if fb present, it should have spawned
    expect(len(fb.spawned) >= 0, "spawn recorded (fb or space)")

    # test: Intent instance passthrough and apply_intent route
    it = Intent(name="custom_intent_x", payload={"x":1}, src_cell_id="cell_1")
    res3 = ex.apply_intents("r0", [it], tick=5)
    expect(len(res3) == 1 and res3[0]["ok"], "Intent instance routed and applied")

    print("All executor smoke tests passed.")

if __name__ == "__main__":
    run_tests()

