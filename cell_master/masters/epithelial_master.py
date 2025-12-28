# cell_master/masters/epithelial_master.py
"""
EpithelialMaster - simple demo implementation for lung epithelial cells.

Design goals:
- Small, deterministic-by-seed state machine for infection / replication / death.
- Minimal external dependencies so tests can instantiate without supplying
  heavy registry/space objects.
- Step accepts: (coord, summary, cell_meta, rng) and returns a list of action dicts:
    {"name": "...", "payload": {...}}
  These get normalized by CellMasterBase when used in full system.

Actions emitted (names):
 - "release_antigen"         payload: {"amount": float, "cell_id":..., "viral_load":...}
 - "spawn_antigen_agents"    payload: {"count": int, "proto": {...}}
 - "mark_fragment"           payload: {"action": "decay" or "handed_over"}
 - "change_state"            payload: {"state": "<new_state>"}
"""

from typing import Dict, Any, List, Optional, Tuple
import random
import math


def _distance(a: Optional[Tuple[float, float]], b: Optional[Tuple[float, float]]) -> float:
    if a is None or b is None:
        return float("inf")
    try:
        return math.hypot(a[0] - b[0], a[1] - b[1])
    except Exception:
        return float("inf")


class EpithelialMaster:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = dict(config or {})

        # infection / exposure
        self.p_infect_on_contact = float(cfg.get("p_infect_on_contact", 0.25))
        self.exposure_radius = float(cfg.get("exposure_radius", 1.5))
        self.incubation_ticks = int(cfg.get("incubation_ticks", 2))
        self.p_establish_infection = float(cfg.get("p_establish_infection", 0.9))

        # replication / release
        self.initial_viral_load = float(cfg.get("initial_viral_load", 1.0))
        self.replication_rate = float(cfg.get("replication_rate", 1.3))
        self.release_interval = int(cfg.get("release_interval", 1))
        self.antigen_release_amount = float(cfg.get("antigen_release_amount", 1.0))

        # necrosis / fragments
        self.damage_to_necrosis_threshold = float(cfg.get("damage_to_necrosis_threshold", 20.0))
        self.prob_necrosis_on_death = float(cfg.get("prob_necrosis_on_death", 0.3))
        self.necrosis_delay = int(cfg.get("necrosis_delay", 1))
        self.antigen_fragment_amount = int(cfg.get("antigen_fragment_amount", 6))
        self.fragment_lifetime = int(cfg.get("fragment_lifetime", 10))

        # misc
        self._debug = bool(cfg.get("debug", False))

        """
        Process one tick for a single epithelial cell.

        - coord: (x,y)
        - summary: context (should include "agents": [agent dicts], optionally others)
        - cell_meta: the mutable metadata for this cell (in-place mutations allowed)
        - rng: an instance of random.Random or None (we create one for determinism)
        Returns: list of action dicts (each with "name" and "payload")
        """

    def step(self, coord, summary, cell_meta, rng):
        actions = []

        # -------------------------------------------------
        # Step2.2 + Step2.3
        # receive CTL apoptosis & release antigen
        # -------------------------------------------------
        ext_intents = summary.get("external_intents") or []
        for intent in ext_intents:
            if intent.get("name") == "external_apoptosis":
                # update state
                cell_meta["state"] = "apoptotic"

                viral = float(cell_meta.get("viral_load", 0.0) or 0.0)

                return [
                    {
                        "name": "die",
                        "payload": {
                            "mode": intent.get("mode", "external_apoptosis"),
                            "source": intent.get("source"),
                        }
                    },
                    {
                        "name": "emit_label",
                        "payload": {
                            "label": "ANTIGEN_RELEASE",
                            "amount": viral,
                            "coord": coord,
                            "source": "epithelial"
                        }
                    }
                ]

        # -------------------------------------------------
        # other epithelial logic (release virus etc.)
        # -------------------------------------------------
        return actions

    # （如果没被杀，下面继续原本逻辑）

        rng = rng or random.Random()
        summary = summary or {}
        cell_meta = cell_meta or {}

        state = cell_meta.get("state", "healthy")
        viral_load = float(cell_meta.get("viral_load", 0.0) or 0.0)
        actions: List[Dict[str, Any]] = []

        # 0) helper debug
        if self._debug:
            print("[Epi] tick: state=", state, "viral=", viral_load)

        # 1) Exposure: check nearby agents for infectious material
        agents = summary.get("agents", []) or []
        for a in agents:
            # Accept variety of agent shapes: expect 'infectious' bool or 'type' / 'mass'
            infectious = a.get("infectious") if isinstance(a, dict) else False
            acoord = a.get("coord") if isinstance(a, dict) else None
            if infectious and _distance(coord, acoord) <= self.exposure_radius:
                if rng.random() < self.p_infect_on_contact * float(cell_meta.get("susceptibility", 1.0)):
                    # become exposed (or immediately infected if p_establish_infection==1)
                    if self.incubation_ticks <= 0 or rng.random() < self.p_establish_infection:
                        # immediate establishment
                        cell_meta["state"] = "infected_productive"
                        cell_meta["viral_load"] = float(cell_meta.get("viral_load", 0.0) or 0.0) + self.initial_viral_load
                        cell_meta["release_timer"] = int(cell_meta.get("release_timer", 0)) or self.release_interval
                        if self._debug:
                            print("[Epi] immediate infection established")
                        break
                    else:
                        cell_meta["state"] = "exposed"
                        cell_meta["incubation_timer"] = int(self.incubation_ticks)
                        if self._debug:
                            print("[Epi] moved to exposed")
                        break

        # 1.5) external apoptosis interrupt (e.g., CTL triggered)
        # If an external trigger is present we expect caller to set cell_meta["external_apoptosis"]=True
        if state == "necrosis_initiated" and cell_meta.get("external_apoptosis"):
            # convert to apoptosis early and cancel necrosis
            cell_meta["state"] = "apoptosis_early"
            cell_meta.pop("necrosis_timer", None)
            cell_meta.pop("external_apoptosis", None)
            actions.append({"name": "change_state", "payload": {"state": "apoptosis_early", "reason": "ctl_interrupt_necrosis"}})
            if self._debug:
                print("[Epi] necrosis interrupted -> apoptosis_early")
            # recompute state variable locally
            state = cell_meta.get("state", state)

        # 2) State transitions & behaviors
        if state == "exposed":
            # tick down incubation
            t = int(cell_meta.get("incubation_timer", self.incubation_ticks))
            t -= 1
            cell_meta["incubation_timer"] = t
            if t <= 0:
                # decide whether infection establishes
                if rng.random() < self.p_establish_infection:
                    cell_meta["state"] = "infected_productive"
                    cell_meta["viral_load"] = float(cell_meta.get("viral_load", 0.0) or 0.0) + self.initial_viral_load
                    cell_meta["release_timer"] = self.release_interval
                    actions.append({"name": "change_state", "payload": {"state": "infected_productive"}})
                    if self._debug:
                        print("[Epi] exposed -> infected_productive")
                else:
                    cell_meta["state"] = "healthy"
                    cell_meta.pop("incubation_timer", None)
                    if self._debug:
                        print("[Epi] exposed -> cleared (healthy)")

        elif state == "infected_productive":
            # replication
            viral_load = float(cell_meta.get("viral_load", 0.0) or 0.0)
            viral_load = viral_load * self.replication_rate
            cell_meta["viral_load"] = viral_load

            # release timer
            rt = int(cell_meta.get("release_timer", self.release_interval))
            rt -= 1
            cell_meta["release_timer"] = rt
            if rt <= 0:
                # produce antigen release intent
                actions.append({
                    "name": "release_antigen",
                    "payload": {
                        "amount": float(self.antigen_release_amount),
                        "cell_state": "infected_productive",
                        "viral_load": viral_load
                    }
                })
                # reset timer
                cell_meta["release_timer"] = self.release_interval
                if self._debug:
                    print("[Epi] release_antigen emitted, viral=", viral_load)

            # possible death / necrosis trigger
            if viral_load >= self.damage_to_necrosis_threshold and rng.random() < self.prob_necrosis_on_death:
                # initiate necrosis
                cell_meta["state"] = "necrosis_initiated"
                cell_meta["necrosis_timer"] = int(self.necrosis_delay)
                actions.append({"name": "change_state", "payload": {"state": "necrosis_initiated"}})
                if self._debug:
                    print("[Epi] necrosis initiated")

                # --- immediate processing when delay == 0: spawn fragments right away ---
                try:
                    nt = int(cell_meta.get("necrosis_timer", self.necrosis_delay) or 0)
                except Exception:
                    nt = int(self.necrosis_delay or 0)
                if nt <= 0:
                    # spawn fragments / antigen agents immediately in same tick
                    actions.append({
                        "name": "spawn_antigen_agents",
                        "payload": {
                            "count": int(self.antigen_fragment_amount),
                            "proto": {"from_cell": True, "state": "fragment"}
                        }
                    })
                    cell_meta["state"] = "fragment"
                    cell_meta["fragment_timer"] = int(self.fragment_lifetime)
                    if self._debug:
                        print("[Epi] necrosis immediate -> fragment; spawned agents:", self.antigen_fragment_amount)
                # update local state variable in case later code in this function checks it
                state = cell_meta.get("state", state)

        elif state == "necrosis_initiated":
            # countdown to fragment release
            nt = int(cell_meta.get("necrosis_timer", self.necrosis_delay))
            nt -= 1
            cell_meta["necrosis_timer"] = nt
            if nt <= 0:
                # spawn many antigen agents / fragments
                actions.append({
                    "name": "spawn_antigen_agents",
                    "payload": {
                        "count": int(self.antigen_fragment_amount),
                        "proto": {"from_cell": True, "state": "fragment"}
                    }
                })
                cell_meta["state"] = "fragment"
                cell_meta["fragment_timer"] = int(self.fragment_lifetime)
                if self._debug:
                    print("[Epi] necrosis -> fragment; spawned agents:", self.antigen_fragment_amount)

        elif state and state.startswith("apoptosis"):
            # simple apoptosis progression: early -> mid -> late -> removed
            stage_order = ["apoptosis_early", "apoptosis_mid", "apoptosis_late"]
            if state not in stage_order:
                # ensure it starts at early if labeled generically
                cell_meta["state"] = "apoptosis_early"
                state = "apoptosis_early"

            # progress counter
            prog = int(cell_meta.get("apoptosis_timer", 2))
            prog -= 1
            cell_meta["apoptosis_timer"] = prog
            idx = stage_order.index(state)
            if prog <= 0 and idx < len(stage_order) - 1:
                # advance stage
                new_state = stage_order[idx + 1]
                cell_meta["state"] = new_state
                cell_meta["apoptosis_timer"] = 2
                actions.append({"name": "change_state", "payload": {"state": new_state}})
                if self._debug:
                    print("[Epi] apoptosis progressed ->", new_state)
            elif prog <= 0 and idx == len(stage_order) - 1:
                # finished -> become fragment (but less infectious)
                cell_meta["state"] = "fragment"
                cell_meta["fragment_timer"] = int(self.fragment_lifetime)
                actions.append({"name": "mark_fragment", "payload": {"action": "apoptotic_fragment"}})
                if self._debug:
                    print("[Epi] apoptosis finished -> fragment")

        elif state == "fragment":
            ft = int(cell_meta.get("fragment_timer", self.fragment_lifetime))
            ft -= 1
            cell_meta["fragment_timer"] = ft
            if ft <= 0:
                actions.append({"name": "mark_fragment", "payload": {"action": "decay"}})
                # remove state to indicate cleaned up / removed entity
                cell_meta.pop("state", None)
                if self._debug:
                    print("[Epi] fragment decayed and removed")

        # 3) Return actions
        return actions

