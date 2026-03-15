import pytest
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.fake_env import FakeEnv
from behaviors_impl.tcr import generate_simple_repertoire, compute_affinity

def test_ctl_kill_flow_minimal():
    # load tcr_scan behavior
    tcfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    tbh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", tcfg)

    # load perforin behavior (behavior file likely exists)
    perf_cfg = load_yaml_rel("behaviors/perforin_apoptosis_v1.yaml")
    perf_bh = instantiate_behavior_from_yaml("behaviors/perforin_apoptosis_v1.yaml", perf_cfg)

    events = []
    intents = []
    env = FakeEnv()
    env.emit_event = lambda n,p: events.append((n,p))
    env.emit_intent = lambda n,p: intents.append((n,p))

    # --- provide compute_affinity on env so tcr_scan can call it ---
    # compute_affinity signature in behaviors_impl.tcr is (clonotype, pmhc)
    env.compute_affinity = lambda pm, tcr: compute_affinity(tcr, pm)
    # ------------------------------------------------------------

    # prepare CTL with repertoire that specifically recognizes S_toy_I_A
    ctl = type("C", (), {})()
    ctl.id = "ctl1"
    ctl.coord = (2,2)
    # simple repertoire: ensure at least one clonotype has specificity S_toy_I_A
    ctl.tcr_repertoire = generate_simple_repertoire(seed=42, size=6, kmer_k=9)
    ctl.tcr_repertoire[0]["specificity"].add("S_toy_I_A")

    # create a pmhc near the CTL
    pmhc = {"pMHC_id":"pm1","peptide_id":"S_toy_I_A","seq":"KQNTLQKYG","mhc_type":"MHC_I","presenter":"dcA"}
    env.collect_pMHC_near = lambda coord, radius: [pmhc]

    # run scan => should emit tcr_scan_result event
    out = tbh.execute(ctl, env, params=tcfg.get("params", {}))
    assert any(e[0] == "tcr_scan_result" for e in events), f"events: {events}"

    # simulate CTL executing perforin release behavior (this impl should emit intent)
    # prepare target cell
    target = type("C", (), {})()
    target.id = "target1"
    target.coord = (3,2)
    # payload typical: {"target_id": target.id, "strength": 1.0}
    perf_bh.execute(ctl, env, params=perf_cfg.get("params", {}), payload={"target_id": target.id, "strength": 1.0})
    # expect an intent to the target or an emitted event
    assert any(t[0] in ("perforin_release", "perforin_apoptosis", "apoptosis") for t in intents + events), f"no kill intents: intents={intents}, events={events}"

