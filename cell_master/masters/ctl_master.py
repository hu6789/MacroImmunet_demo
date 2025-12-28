# cell_master/masters/ctl_master.py
# -*- coding: utf-8 -*-
from typing import List, Optional, Dict, Any

# 兼容性：不强制调用 BaseMaster.__init__，以便 tests 可以零参构造
# 如果将来需要把实例真正接入运行时，可以把 space/registry 注入到实例上。
# from cell_master.base_master import BaseMaster

from cell_master.intents import (
    Intent_perforin_release,
    Intent_granzyme_release,
    Intent_fasl_trigger,
    Intent_trigger_apoptosis,
    Intent_move_to,
    Intent_random_move,
)


# Compatibility: tests may supply neighbors under different keys in summary.
_NEIGHBOR_KEYS = ("neighbors", "nearby_cells", "neighbor_cells", "cells")


class CTLMaster:
    """
    Simple CTL master for demo/tests.

    step(coord, summary, cell_meta, rng) -> List[Intent-like objects]

    Rules:
     - If summary contains 'pMHC_hotspot' -> move_to(hotspot)
     - Else look for nearby target cells (from summary)
       prefer states: infected -> apoptosis_early -> apoptosis_mid
     - If target is infected or apoptosis_early -> full kill (perforin+granzyme+trigger_apoptosis)
     - If target is apoptosis_mid -> cleanup kill (trigger_apoptosis + optional perforin)
     - Else -> random_move
    """

    def __init__(self, cell_type: str = "CTL", kill_radius: float = 1.5, **kwargs):
        """
        Zero-arg-safe constructor for tests.

        - cell_type: optional label
        - kill_radius: numeric radius for neighbor targeting
        - kwargs ignored (allows future injection)
        """
        # keep basic identity fields so tests / other code can inspect instance
        self.cell_type = cell_type
        self.kill_radius = float(kill_radius)

        # runtime attachments (optional) - can be injected later if needed
        self.space = kwargs.get("space", None)
        self.behaviour_registry = kwargs.get("behaviour_registry", None)
        self.feedback = kwargs.get("feedback", None)

    def step(self, coord: Optional[tuple], summary: Dict[str, Any], cell_meta: Dict[str, Any], rng) -> List[Any]:
        # 1) pMHC hotspot guidance
        if summary and "pMHC_hotspot" in summary and summary.get("pMHC_hotspot") is not None:
            hotspot = summary["pMHC_hotspot"]
            return [Intent_move_to(coord=coord, target=hotspot)]

        # 2) collect neighbor cells supplied in summary (tests provide these)
        neighbors = None
        for k in _NEIGHBOR_KEYS:
            if summary and k in summary and isinstance(summary[k], list):
                neighbors = summary[k]
                break
        if neighbors is None:
            # no neighborhood info -> random move
            return [Intent_random_move(coord=coord)]

        # 3) pick a target according to preferred states
        target = self._select_target(neighbors)
        if target is None:
            return [Intent_random_move(coord=coord)]

        state = target.get("state")
        tcoord = target.get("coord")

        # 4) decide kill or cleanup
        if state in ("infected", "apoptosis_early"):
            return self._emit_full_kill(coord, tcoord)
        if state == "apoptosis_mid":
            return self._emit_cleanup_kill(coord, tcoord)

        # fallback
        return [Intent_random_move(coord=coord)]

    def _select_target(self, neighbors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Return the highest-priority neighbor to attack:
        priority order infected < apoptosis_early < apoptosis_mid (lower is better)
        neighbors are dicts with at least 'state' and 'coord'
        """
        if not neighbors:
            return None

        # filter only those with coord and state
        cand = [n for n in neighbors if n.get("state") and n.get("coord") is not None]
        if not cand:
            return None

        priority_map = {"infected": 0, "apoptosis_early": 1, "apoptosis_mid": 2}
        # sort by priority (unknown states go last)
        cand.sort(key=lambda x: priority_map.get(x.get("state"), 99))
        # return first with acceptable state
        top = cand[0]
        if priority_map.get(top.get("state"), 99) < 99:
            return top
        return None

    def _emit_full_kill(self, source_coord, target_coord):
        """Perforin + granzyme + fasl + unified trigger_apoptosis"""
        intents = []
        intents.append(Intent_perforin_release(source=source_coord, target=target_coord))
        intents.append(Intent_granzyme_release(source=source_coord, target=target_coord))
        # FasL often slower/alternative; include for completeness
        intents.append(Intent_fasl_trigger(source=source_coord, target=target_coord))
        # finalize with an apoptosis trigger
        intents.append(Intent_trigger_apoptosis(source=source_coord, target=target_coord, reason="ctl_full_kill"))
        return intents

    def _emit_cleanup_kill(self, source_coord, target_coord):
        """Cleanup: emit a minimal set (trigger apoptosis; optionally perforin)"""
        intents = []
        # small perforin to accelerate collapse + final trigger
        intents.append(Intent_perforin_release(source=source_coord, target=target_coord, amount=0.5))
        intents.append(Intent_trigger_apoptosis(source=source_coord, target=target_coord, reason="ctl_cleanup"))
        return intents


# export
__all__ = ["CTLMaster"]

