# -*- coding: utf-8 -*-

from cell_master.masters.dc_master import DCMaster
from cell_master.intents import Intent


def test_dc_master_contract_basic():
    """
    Contract test for DCMaster (Step1: interface only).

    Expectations:
    - can be constructed without args
    - has handle_label method
    - handle_label returns List[Intent]
    - always emits at least one movement intent
    - when captured_antigens exist, emits antigen-related intent
    """
    dc = DCMaster()

    assert hasattr(dc, "handle_label"), "DCMaster must implement handle_label"

    label = {
        "id": "dc_test_1",
        "coord": (0.0, 0.0),
        "meta": {
            "captured_antigens": [
                {"epitopes": [{"seq": "AAA"}]}
            ]
        }
    }

    intents = dc.handle_label(
        region_id="test_region",
        label=label,
        node_meta={},
        tick=0,
    )

    # --- basic shape ---
    assert isinstance(intents, list), "handle_label must return a list"
    assert all(isinstance(i, Intent) for i in intents), "all outputs must be Intent"

    names = [i.name for i in intents]

    # --- movement is mandatory ---
    assert "move_to" in names, "DCMaster must emit a move_to intent"

    # --- antigen processing / presentation ---
    assert (
        "phagocytose" in names or "pMHC_presented" in names
    ), "DCMaster must emit antigen-related intent when captured_antigens exist"

