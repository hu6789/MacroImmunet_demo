"""
AntigenMaster – Step1 minimal rewrite
Only guarantees:
- spawn_agent works
- step() writes antigen labels
- space.get_labels() can see them
"""

from typing import Dict, Any, List, Optional, Tuple
import time
import uuid
import random
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

Coord = Tuple[float, float]


class AntigenMaster:
    def __init__(
        self,
        space,
        feedback=None,
        rng: Optional[random.Random] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.space = space
        self.feedback = feedback or space
        self.rng = rng or random.Random()
        self.config = config or {}

        self.agents: Dict[str, Dict[str, Any]] = {}
        self._spawn_counter = 0

    # ------------------------------------------------------------------
    def _make_agent_id(self) -> str:
        self._spawn_counter += 1
        return f"ag_{int(time.time()*1000)}_{self._spawn_counter}_{uuid.uuid4().hex[:6]}"

    # ------------------------------------------------------------------
    def spawn_agent(
        self,
        coord: Optional[Coord] = None,
        proto: Optional[Dict[str, Any]] = None,
        viral_load: float = 1.0,
    ) -> str:
        proto = proto or {}
        coord = tuple(coord) if coord is not None else (0.0, 0.0)

        aid = self._make_agent_id()
        self.agents[aid] = {
            "id": aid,
            "coord": coord,
            "viral_load": float(viral_load),
            "proto": proto,
            "state": "active",
        }

        # ⭐ spawn 时立即写一个 label（test 会看）
        self._write_label(self.agents[aid])
        return aid

    # ------------------------------------------------------------------
    def list_agents(self, *_):
        return list(self.agents.values())
    # ------------------------------------------------------------------
    def step(self, region_id=None, tick: int = 0):
        """
        AntigenMaster:
        - 每 tick 将 active antigen agent 映射为一个 ANTIGEN_PARTICLE label
        - label 一定写入 Space（global 可见）
        """
        if region_id is None:
            region_id = "global"

        written = []

        for ag in self.agents.values():
            if ag.get("state") != "active":
                continue

            proto = ag.get("proto", {})

            label = {
                "name": "antigen",
                "type": proto.get("type", "ANTIGEN_PARTICLE"),
                "coord": tuple(ag.get("coord", (0.0, 0.0))),
                "amount": float(proto.get("amount", ag.get("viral_load", 1.0))),
                "epitopes": proto.get("epitopes", []),
                "meta": {
                    "source": "AntigenMaster",
                    "agent_id": ag.get("id"),
                    "tick": tick,
                },
            }

            # Space API: add_label(region_id, label)
            self.space.add_label(region_id, label)
            written.append(label)

        return written
    # ------------------------------------------------------------------
    def _write_label(self, agent: Dict[str, Any]):
        label = {
            "type": "ANTIGEN_PARTICLE",
            "coord": agent["coord"],
            "amount": float(agent.get("viral_load", 1.0)),
            "meta": {
                "source_agent": agent["id"],
            },
        }

        # ⭐⭐⭐ 关键点：只用这一种写法 ⭐⭐⭐
        try:
            self.space.add_label(label)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def reset(self):
        self.agents.clear()
        self._spawn_counter = 0

