# -*- coding: utf-8 -*-

from cell_master.masters.th1_master import Th1Master


def test_th1_master_contract_basic():
    th1 = Th1Master()

    assert hasattr(th1, "step")

    actions = th1.step(
        coord=(0.0, 0.0),
        summary={},
        cell_meta={},
        rng=None,
    )

    assert isinstance(actions, list)
    assert len(actions) >= 1


def test_th1_master_can_handle_activation_flag():
    th1 = Th1Master()

    actions = th1.step(
        coord=(0.0, 0.0),
        summary={},
        cell_meta={"activated": True},
        rng=None,
    )

    assert isinstance(actions, list)
    assert actions[0] is not None

