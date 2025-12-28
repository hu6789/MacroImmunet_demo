# test/test_dc_master.py
import sys, os
sys.path.append(os.path.abspath("."))

from cell_master.masters.dc_master import DCMaster
from cell_master.gene_gate import GeneGate
from cell_master.intents import Intent
import random

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def run_all():
    rng = random.Random(42)
    gm = GeneGate({})
    config = {"mhc_type": "MHC_I", "process_limit": 2, "default_ln_coord": (50.0, 50.0), "random_step_size": 1.5}
    dm = DCMaster(space=None, registry=None, feedback=None, gene_gate=gm, config=config, rng=rng)

    # case 1: label with captured_antigens -> phagocytose + pMHC_presented + directed move
    label = {"id": "dc_1", "coord": (0.0, 0.0), "meta": {"captured_antigens": [{"epitopes":[{"seq":"PEP1"}], "sequence":"AAAA"}, {"epitopes":[{"seq":"PEP2"}], "sequence":"BBBB"}]}}
    node_meta = {"target": "LN", "process_limit": 1}
    intents = dm.handle_label("r0", label, node_meta=node_meta, tick=1)
    names = [it.name for it in intents]
    expect("phagocytose" in names, "phagocytose intent emitted when antigens present")
    expect(any(n == "pMHC_presented" for n in names), "pMHC_presented intent emitted")
    expect(any(n == "move_to" for n in names), "move_to intent emitted after presentation")

    # case 2: label without antigen -> only random move (and no phagocytose/present)
    label2 = {"id": "dc_2", "coord": (10.0, 5.0), "meta": {}}
    intents2 = dm.handle_label("r0", label2, node_meta={}, tick=1)
    names2 = [it.name for it in intents2]
    expect("phagocytose" not in names2, "no phagocytose when no antigen")
    expect("pMHC_presented" not in names2, "no presentation when no antigen")
    expect("move_to" in names2 and any(it.payload.get("mode") == "random" for it in intents2), "random move emitted when no antigen")

    # case 3: hotspot override -> directed to hotspot
    label3 = {"id": "dc_3", "coord": (1.0, 0.0), "meta": {"captured_antigens":[{"epitopes":[{"seq":"X"}], "sequence":"X"}]}}
    node_meta3 = {"hotspot_coord": (5.0, 5.0)}
    intents3 = dm.handle_label("r0", label3, node_meta=node_meta3, tick=1)
    move_intents = [it for it in intents3 if it.name == "move_to"]
    expect(len(move_intents) == 1, "one move_to when presented")
    target = move_intents[0].payload.get("to")
    expect(tuple(target) == (5.0, 5.0), "directed move targets hotspot_coord")

    print("All DCMaster tests passed.")

if __name__ == "__main__":
    run_all()

