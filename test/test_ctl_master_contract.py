# test/test_ctl_master_contract.py
# -*- coding: utf-8 -*-
from cell_master.masters.ctl_master import CTLMaster
from cell_master.intents import Intent_move_to, Intent_trigger_apoptosis

def test_ctl_master_basic_contract():
    m = CTLMaster()

    summary = {
        "neighbors": [
            {"state": "infected", "coord": (1.0, 1.0)},
        ]
    }

    out = m.step(
        coord=(0.0, 0.0),
        summary=summary,
        cell_meta={},
        rng=None,
    )

    # ---- contract assertions ----
    assert isinstance(out, list)
    assert len(out) > 0

    # 至少产生一个 intent
    assert any(
        hasattr(intent, "__class__")
        for intent in out
    )

    # infected target -> 必须触发 apoptosis
    assert any(
        isinstance(intent, Intent_trigger_apoptosis)
        for intent in out
    )

