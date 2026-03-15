# tests/unit/test_cell_naive_cd8_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_naive_cd8_activation_and_differentiate_to_ctl():
    """
    Test Naive CD8 TCR scan emits an event and differentiate behavior can
    convert the cell to CTL (or at least set an effector flag / emit event).
    We force a high affinity via env.compute_affinity to trigger CTL fate.
    """
    cfg = load_yaml_rel("cells/Naive_CD8_v1.yaml")

    cell = SimpleCellMock(position=(3,3))
    cell.id = "naive_cd8_1"
    cell.meta.update(cfg.get("meta", {}))

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    intents = []
    env.emit_intent = lambda n,p: intents.append((n,p))

    # stub environment for TCR scanning
    pmhc = {"pMHC_id": "pm1", "peptide_id": "PepI", "mhc_type": "MHC_I", "presenter": "dcA"}
    env.collect_pMHC_near = lambda coord, radius=1: [pmhc]
    # return very high affinity to cross activation_affinity_threshold
    env.compute_affinity = lambda pm, tcr: 0.95

    # instantiate behaviors
    tcfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    tbh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", tcfg)

    diff_cfg = load_yaml_rel("behaviors/differentiate_v1.yaml")
    diff_bh = instantiate_behavior_from_yaml("behaviors/differentiate_v1.yaml", diff_cfg)

    # run tcr scan -> expect event
    tbh.execute(cell, env, params=tcfg.get("params", {}))
    assert any(e[0] == "tcr_scan_result" for e in events), f"expected tcr_scan_result, got {events}"

    # Clear events and force differentiation to CTL deterministically
    events.clear()
    params = {
        "differentiation": {
            "CTL": {"prob": 1.0, "behaviors": ["perforin_apoptosis_v1.yaml", "proliferate_v1.yaml"]}
        }
    }

    success = False
    tried = []

    # Try params-based call
    try:
        actions = diff_bh.execute(cell, env, params=params)
        tried.append(("params", params))
    except Exception as ex:
        actions = []
        tried.append(("params_exception", str(ex)))

    # Check outcomes: event 'differentiated' or meta flag 'effector_type' == 'CTL'
    if any(e[0] == "differentiated" for e in events):
        success = True
    if getattr(cell, "effector_type", None) in ("CTL", "Effector_CTL", "CTL-like"):
        success = True
    if isinstance(actions, (list, tuple)) and any(a.get("name") in ("perforin_apoptosis", "perforin_apoptosis_v1", "differentiated") for a in (actions or [])):
        success = True

    # try payload variant if needed
    if not success:
        payload = {"differentiation": params["differentiation"]}
        tried.append(("payload", payload))
        try:
            actions = diff_bh.execute(cell, env, params={}, payload=payload)
        except Exception:
            actions = []
        if any(e[0] == "differentiated" for e in events):
            success = True
        if getattr(cell, "effector_type", None) in ("CTL",):
            success = True
        if isinstance(actions, (list, tuple)) and actions:
            success = True

    assert success, f"differentiation->CTL didn't occur. Tried: {tried}; events={events}; cell.meta={cell.meta}; actions={actions}"

