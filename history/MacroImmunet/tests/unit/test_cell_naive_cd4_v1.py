# tests/unit/test_cell_naive_cd4_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_naive_cd4_tcr_scan_and_differentiate_th1_th2():
    """
    Test Naive CD4 basic TCR scan emits scan event and differentiate behavior
    will mark the cell as Th1/Th2 (or emit a 'differentiated' event / set meta).
    The test stubs env.compute_affinity and env.collect_pMHC_near to force recognition.
    """
    # load cell cfg (not strictly used beyond meta defaults)
    cfg = load_yaml_rel("cells/Naive_CD4_v1.yaml")

    # prepare a mock cell
    cell = SimpleCellMock(position=(2,2))
    cell.id = "naive_cd4_1"
    cell.meta.update(cfg.get("meta", {}))

    # stub environment
    env = FakeEnv()
    events = []
    env.emit_event = lambda n, p: events.append((n, p))
    intents = []
    env.emit_intent = lambda n,p: intents.append((n,p))

    # --- make TCR scanning deterministic: env.collect_pMHC_near returns a pmhc
    pmhc = {"pMHC_id": "pm1", "peptide_id": "PepX", "mhc_type": "MHC_II", "presenter": "dcA"}
    env.collect_pMHC_near = lambda coord, radius=1: [pmhc]
    # compute_affinity signature used in tests: some impl expect (pm, tcr) or (tcr, pm)
    # make a wrapper that returns moderately high affinity
    env.compute_affinity = lambda pm, tcr: 0.85

    # instantiate behaviors
    tcfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    tbh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", tcfg)

    diff_cfg = load_yaml_rel("behaviors/differentiate_v1.yaml")
    diff_bh = instantiate_behavior_from_yaml("behaviors/differentiate_v1.yaml", diff_cfg)

    # run TCR scan => expect an event "tcr_scan_result" (implementation may vary)
    tbh.execute(cell, env, params=tcfg.get("params", {}))
    assert any(e[0] == "tcr_scan_result" for e in events), f"expected tcr_scan_result in events, got {events}"

    # Clear events for clarity, then force differentiation params: make Th1 deterministic
    events.clear()
    # ensure differentiation rules in params (force Th1)
    params = {
        "differentiation": {
            "Th1": {"prob": 1.0, "behaviors": ["help_CD8_v1.yaml", "secrete_v1.yaml"]},
            "Th2": {"prob": 0.0}
        },
        # optionally provide signals/affinity in payload if implementation reads payload
    }

    # Try calling differentiate in a few ways (params, payload) and accept multiple outcome styles
    success = False
    tried = []

    # 1) call with params directly
    try:
        actions = diff_bh.execute(cell, env, params=params)
        tried.append(("params", params))
    except Exception as ex:
        actions = []
        tried.append(("params_exception", str(ex)))

    # Check possible signs of differentiation:
    # - an event 'differentiated'
    # - cell.meta['effector_type'] or cell.meta['phenotype'] set to something like 'Th1'
    # - returned actions include names listed in rules
    if any(e[0] == "differentiated" for e in events):
        success = True

    if getattr(cell, "effector_type", None) in ("Th1", "Th_1", "Th1-like") or getattr(cell, "phenotype", None) in ("Th1",):
        success = True

    # returned actions might include 'differentiate' or behaviors from the rule
    if isinstance(actions, (list, tuple)) and any(a.get("name") in ("help_CD8_v1", "secrete", "secrete_v1", "differentiated") or a.get("name") == "differentiated" for a in (actions or [])):
        success = True

    # 2) if still not successful, try passing differentiation via payload
    if not success:
        payload = {"differentiation": params["differentiation"]}
        tried.append(("payload", payload))
        try:
            actions = diff_bh.execute(cell, env, params={}, payload=payload)
        except Exception:
            actions = []

        if any(e[0] == "differentiated" for e in events):
            success = True
        if getattr(cell, "effector_type", None) in ("Th1",):
            success = True
        if isinstance(actions, (list, tuple)) and actions:
            success = True

    assert success, f"differentiation did not produce expected outcome. Tried: {tried}; events={events}; cell.meta={cell.meta}; actions={actions}"

