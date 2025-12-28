# -*- coding: utf-8 -*-

from cell_master.masters.native_t_master import NativeTMaster


def test_native_t_master_contract_basic():
    """
    Contract test for NativeTMaster (Step1).

    Expectations:
    - zero-arg construction
    - has step method
    - step returns list of action dicts
    - each action has a 'name'
    """

    nt = NativeTMaster()

    assert hasattr(nt, "step"), "NativeTMaster must implement step()"

    coord = (0.0, 0.0)
    summary = {}
    cell_meta = {"type": "NAIVE_T"}

    actions = nt.step(coord, summary, cell_meta, rng=None)

    assert isinstance(actions, list), "step() must return a list"
    assert len(actions) > 0, "step() must return at least one action"

    for a in actions:
        assert isinstance(a, dict), "actions must be dicts"
        assert "name" in a, "each action must have a name"


def test_native_t_master_random_move_when_idle():
    """
    NAIVE_T with no cues should wander.
    """

    nt = NativeTMaster()

    actions = nt.step(
        coord=(1.0, 1.0),
        summary={},
        cell_meta={"type": "NAIVE_T"},
        rng=None,
    )

    names = [a["name"] for a in actions]
    assert "random_move" in names, "NAIVE_T should random_move when idle"


def test_native_t_master_differentiation_on_pmhc():
    """
    Strong pMHC cue should be able to trigger differentiation / handover.
    (Probabilistic, so we try multiple times.)
    """

    nt = NativeTMaster()

    summary = {"pMHC_present": True}
    cell_meta = {"type": "NAIVE_T"}

    seen_diff = False
    for _ in range(20):
        acts = nt.step(coord=None, summary=summary, cell_meta=cell_meta, rng=None)
        names = [a["name"] for a in acts]
        if "change_type" in names or "handover_label" in names:
            seen_diff = True
            break

    assert seen_diff, "NativeTMaster should sometimes differentiate on pMHC cue"

