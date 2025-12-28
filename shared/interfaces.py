# shared/interfaces.py
"""
Shared schema definitions for MacroImmunet_demo.

Provides:
  - Label (dict-compatible dataclass-like helpers)
  - Agent
  - Snapshot
  - Node schema (used by aggregator / node_builder / scan master)
  - small factory helpers
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import time

Tick = int
Coord = Tuple[float, float]


@dataclass
class Label:
    id: str
    name: str
    type: str
    mass: float = 1.0
    coord: Optional[Coord] = None
    owner: Optional[str] = None
    created_tick: Tick = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "mass": self.mass,
            "coord": self.coord,
            "owner": self.owner,
            "created_tick": self.created_tick,
            "meta": self.meta,
        }


@dataclass
class Agent:
    id: str
    proto: Dict[str, Any]
    coord: Optional[Coord] = None
    state: str = "idle"
    created_ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proto": self.proto,
            "coord": self.coord,
            "state": self.state,
            "created_ts": self.created_ts,
            "meta": self.meta,
        }


@dataclass
class SnapshotRegion:
    labels: List[Dict[str, Any]]
    agents: List[Dict[str, Any]]
    hotspots: List[Dict[str, Any]]
    summary: Dict[str, Any]


@dataclass
class Snapshot:
    grid: Optional[Dict[str, Any]]
    regions: Dict[str, SnapshotRegion]
    owners: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid": self.grid,
            "regions": {k: {
                "labels": v.labels,
                "agents": v.agents,
                "hotspots": v.hotspots,
                "summary": v.summary
            } for k, v in self.regions.items()},
            "owners": self.owners
        }


@dataclass
class Node:
    node_id: str
    node_type: str
    coord: Optional[Coord] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    targets: List[str] = field(default_factory=list)
    priority: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "coord": self.coord,
            "inputs": self.inputs,
            "targets": self.targets,
            "priority": self.priority,
            "meta": self.meta
        }


# Nice small helper constructors to keep tests concise
def make_label_dict(label_id: str, name: str, ltype: Optional[str] = None, coord: Optional[Coord] = None,
                    mass: float = 1.0, owner: Optional[str] = None, tick: int = 0, meta: Optional[Dict] = None) -> Dict[str, Any]:
    return Label(
        id=label_id,
        name=name,
        type=(ltype or name),
        mass=mass,
        coord=coord,
        owner=owner,
        created_tick=tick,
        meta=meta or {}
    ).to_dict()


def make_agent_dict(agent_id: str, proto: Dict[str, Any], coord: Optional[Coord] = None, state: str = "idle",
                    meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return Agent(id=agent_id, proto=proto, coord=coord, state=state, meta=meta or {}).to_dict()

