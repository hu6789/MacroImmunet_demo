#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AntigenMaster CONTRACT test
---------------------------
This test only checks AntigenMaster's own responsibility:

1. Can spawn antigen agents
2. step() emits antigen-like semantic outputs
3. Emitted objects have minimal expected structure

It does NOT assume:
- space commit timing
- DCMaster presence
- label visibility in world
"""

import inspect
import random

# --- import AntigenMaster ----------------------------------------------------
try:
    from cell_master.masters.antigen_master import AntigenMaster
except Exception as e:
    raise SystemExit(f"Cannot import AntigenMaster: {e}")

# --- minimal dummy space -----------------------------------------------------
class DummySpace:
    def __init__(self):
        self.labels = []

    def add_label(self, *args, **kwargs):
        # accept any signature; record last arg if dict-like
        if args:
            maybe_label = args[-1]
            if isinstance(maybe_label, dict):
                self.labels.append(maybe_label)

    def get_labels(self):
        return list(self.labels)

# --- helpers ----------------------------------------------------------------
def is_antigen_like(obj) -> bool:
    if not isinstance(obj, dict):
        return False

    t = obj.get("type") or obj.get("name", "")
    if "ANTIGEN" not in str(t).upper():
        return False

    # amount / load is expected
    if not any(k in obj for k in ("amount", "value", "viral_load")):
        return False

    return True


# ============================================================================
# TEST
# ============================================================================

def test_antigen_master_contract():
    space = DummySpace()

    # --- instantiate AntigenMaster robustly ---------------------------------
    sig = inspect.signature(AntigenMaster)

    try:
        ant = AntigenMaster(space)
    except TypeError:
        ant = AntigenMaster(space=space)

    # --- must have spawn_agent & step ---------------------------------------
    assert hasattr(ant, "spawn_agent"), "AntigenMaster missing spawn_agent()"
    assert hasattr(ant, "step"), "AntigenMaster missing step()"

    # --- spawn a valid antigen agent ----------------------------------------
    proto = {
        "type": "ANTIGEN_PARTICLE",
        "amount": 1.0,
        "epitopes": [{"seq": "PEPX"}],
    }

    try:
        agent_id = ant.spawn_agent(coord=(0.0, 0.0), proto=proto)
    except TypeError:
        agent_id = ant.spawn_agent((0.0, 0.0), proto)

    assert agent_id is not None, "spawn_agent() returned None"

    # --- run step & collect outputs -----------------------------------------
    outputs = []

    for _ in range(5):
        try:
            res = ant.step("test_region")
        except TypeError:
            res = ant.step()

        if res:
            outputs.extend(res)

    # --- ASSERTIONS ----------------------------------------------------------
    assert outputs, "AntigenMaster.step() produced no outputs"

    antigen_outputs = [o for o in outputs if is_antigen_like(o)]

    assert antigen_outputs, (
        "step() outputs exist but none look like antigen labels.\n"
        f"Outputs: {outputs}"
    )

    # --- minimal semantic checks --------------------------------------------
    sample = antigen_outputs[0]

    assert "epitopes" in sample, "Antigen label missing epitopes"
    assert isinstance(sample["epitopes"], list), "epitopes must be list"

    print("\n[OK] AntigenMaster contract satisfied.")
    print("Sample antigen output:")
    print(sample)


# --- standalone run ----------------------------------------------------------
if __name__ == "__main__":
    test_antigen_master_contract()

