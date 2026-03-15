# tests/unit/test_tcell_lineage_spec.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call_behavior(bh, cell, env, params=None, payload=None):
    """Helper that tries both execute(...) and function-style call adapter used in harness."""
    params = params or {}
    payload = payload or {}
    try:
        return bh.execute(cell, env, params=params, payload=payload)
    except Exception:
        # some adapters in repo accept different call signature
        try:
            return bh(cell, env, params=params, payload=payload)
        except Exception:
            return []

def test_cd4_naive_to_th1_via_spec():
    spec = load_yaml_rel("specs/T_cell_lineage.yaml")
    # find the transition Naive_CD4 -> Effector_Th1
    transt = None
    for t in spec.get("transitions", []):
        if t.get("from") == "Naive_CD4" and t.get("to") == "Effector_Th1":
            transt = t
            break
    assert transt, "transition Naive_CD4 -> Effector_Th1 not found in spec"

    # make deterministic: force probability to 1.0 in params we will pass to behavior
    diff_cfg = load_yaml_rel("behaviors/differentiate_v1.yaml")
    diff_bh = instantiate_behavior_from_yaml("behaviors/differentiate_v1.yaml", diff_cfg)

    # prepare cell/env
    cell = SimpleCellMock(position=(5,5))
    cell.id = "naive_cd4_test"
    # mock meta default if any
    cell.meta.update({"last_scan": {}, "effector_type": None})

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    # provide environment so TCR affinity and cytokine checks would be true if used:
    # ensure compute_affinity returns strong value and fields return IL12 >= required
    env.compute_affinity = lambda pm, tcr: 0.9
    env.get_at = lambda fname, coord: 0.5 if fname == "Field_IL12" or fname == "Field_IL12_conc" else 0.0
    env.collect_pMHC_near = lambda coord, radius=1: [{"pMHC_id":"pm1","peptide_id":"X","mhc_type":"MHC_II"}]

    # call differentiate with payload forcing target_state from spec 'to'
    payload = {"target_state": transt.get("to"), "probability": 1.0, "cause": "spec_test"}
    actions = _call_behavior(diff_bh, cell, env, params={}, payload=payload)

    # assert either state changed, meta set, or event emitted as acceptable outcomes
    assert getattr(cell, "state", None) in (transt.get("to"), transt.get("to").replace("Effector_", ""))
    assert any(e[0] == "differentiated" for e in events) or actions, f"no differentiation observed: events={events}, actions={actions}"

def test_cd4_naive_to_th2_via_spec():
    spec = load_yaml_rel("specs/T_cell_lineage.yaml")
    transt = None
    for t in spec.get("transitions", []):
        if t.get("from") == "Naive_CD4" and t.get("to") == "Effector_Th2":
            transt = t
            break
    assert transt, "transition Naive_CD4 -> Effector_Th2 not found in spec"

    diff_cfg = load_yaml_rel("behaviors/differentiate_v1.yaml")
    diff_bh = instantiate_behavior_from_yaml("behaviors/differentiate_v1.yaml", diff_cfg)

    cell = SimpleCellMock(position=(6,6))
    cell.id = "naive_cd4_test2"
    cell.meta.update({})

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    env.compute_affinity = lambda pm, tcr: 0.8
    env.get_at = lambda fname, coord: 0.5 if fname == "Field_IL4" else 0.0
    env.collect_pMHC_near = lambda coord, radius=1: [{"pMHC_id":"pm2","peptide_id":"Y","mhc_type":"MHC_II"}]

    payload = {"target_state": transt.get("to"), "probability": 1.0, "cause": "spec_test"}
    actions = _call_behavior(diff_bh, cell, env, params={}, payload=payload)

    assert getattr(cell, "state", None) in (transt.get("to"),)
    assert any(e[0] == "differentiated" for e in events) or actions

def test_cd8_naive_to_ctl_via_spec():
    spec = load_yaml_rel("specs/T_cell_lineage.yaml")
    transt = None
    for t in spec.get("transitions", []):
        if t.get("from") == "Naive_CD8" and t.get("to") == "Effector_CTL":
            transt = t
            break
    assert transt, "transition Naive_CD8 -> Effector_CTL not found in spec"

    diff_cfg = load_yaml_rel("behaviors/differentiate_v1.yaml")
    diff_bh = instantiate_behavior_from_yaml("behaviors/differentiate_v1.yaml", diff_cfg)

    cell = SimpleCellMock(position=(7,7))
    cell.id = "naive_cd8_test"
    cell.meta.update({})

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    env.compute_affinity = lambda pm, tcr: 0.95
    env.collect_pMHC_near = lambda coord, radius=1: [{"pMHC_id":"pm3","peptide_id":"Z","mhc_type":"MHC_I"}]
    # if the spec required 'help_from_Th1', we simulate helper presence via env.has_help (some impls may check that)
    env.has_help_from_Th1 = lambda coord: True
    # also provide a generic getter used by some code-paths
    env.get_at = lambda fname, coord: 1.0

    payload = {"target_state": transt.get("to"), "probability": 1.0, "cause": "spec_test"}
    actions = _call_behavior(diff_bh, cell, env, params={}, payload=payload)

    assert getattr(cell, "state", None) in (transt.get("to"),)
    assert any(e[0] == "differentiated" for e in events) or actions

def test_effector_to_memory_conversion_via_spec():
    spec = load_yaml_rel("specs/T_cell_lineage.yaml")
    # find first effector->memory mapping in spec
    mem_trans = None
    for t in spec.get("transitions", []):
        if t.get("trigger", {}).get("type", "") == "post_effector_conversion":
            mem_trans = t
            break
    assert mem_trans, "no effector->memory transition found in spec"

    # call become_memory behavior directly
    mem_cfg = load_yaml_rel("behaviors/become_memory_v1.yaml")
    mem_bh = instantiate_behavior_from_yaml("behaviors/become_memory_v1.yaml", mem_cfg)

    cell = SimpleCellMock(position=(8,8))
    cell.id = "effector_test"
    # set starting state to the 'from' effector so become_memory has something to convert
    cell.state = mem_trans.get("from")
    cell.meta.update({})

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    # force probability to 1.0 to ensure conversion
    params = {"probability": 1.0}
    actions = _call_behavior(mem_bh, cell, env, params=params, payload={})

    # outcome: either cell.state becomes the 'to', or become_memory writes meta or emits event
    assert getattr(cell, "state", None) in (mem_trans.get("to"),) or any(e[0] == "became_memory" for e in events) or actions

