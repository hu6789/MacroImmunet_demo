# scan_master/space_adapter.py
from typing import Any, Dict, List, Tuple

class SpaceAdapter:
    """
    Uniform adapter for any Space / World implementation.
    Ensures a consistent interface:
        - list_labels
        - list_agents
        - add_label
        - remove_label
        - get_grid_summary
        - snapshot
    """

    def __init__(self, space_obj: Any, region_default: str = "epi_1"):
        self.space = space_obj
        self.region_default = region_default

    # -----------------------------
    # LABELS
    # -----------------------------
    def list_labels(self, region: Any = None) -> List[Dict]:
        if hasattr(self.space, "get_labels"):
            labels = self.space.get_labels(region or self.region_default)
            return [self._normalize_label(lb) for lb in labels]
        return []

    def add_label(self, label: Dict):
        """Always go through the space.add_label if it exists"""
        if hasattr(self.space, "add_label"):
            return self.space.add_label(label)
        raise NotImplementedError("space.add_label() missing")

    def remove_label(self, label_id: str):
        if hasattr(self.space, "remove_label"):
            return self.space.remove_label(label_id)
        # silently ignore if removal not supported
        return False

    # -----------------------------
    # AGENTS
    # -----------------------------
    def list_agents(self, region: Any = None) -> List[Dict]:
        if hasattr(self.space, "get_agents"):
            ag = self.space.get_agents(region or self.region_default)
            return [self._normalize_agent(a) for a in ag]
        return []

    # -----------------------------
    # SNAPSHOT
    # -----------------------------
    def snapshot(self) -> Dict:
        """Return a consistent snapshot structure"""
        snap = {
            "grid": None,
            "labels": self.list_labels(),
            "agents": self.list_agents(),
            "fields": {},
        }

        if hasattr(self.space, "snapshot"):
            raw = self.space.snapshot()
            if isinstance(raw, dict):
                # merge known keys if present
                snap.update({
                    "grid": raw.get("grid", None),
                    "labels": raw.get("labels", snap["labels"]),
                    "agents": raw.get("agents", snap["agents"]),
                    "fields": raw.get("fields", {}),
                })
        return snap

    # -----------------------------
    # GRID SUMMARY
    # -----------------------------
    def get_grid_summary(self, region=None) -> Dict:
        """Convert labels into a per-grid summary"""
        labels = self.list_labels(region)
        summary = {}
        for lb in labels:
            coord = tuple(lb.get("coord", (0, 0)))
            mass = lb.get("mass", 1)
            t = lb.get("type", "UNKNOWN")

            if coord not in summary:
                summary[coord] = {}
            if t not in summary[coord]:
                summary[coord][t] = 0
            summary[coord][t] += mass
        return summary

    # -----------------------------
    # Normalizers
    # -----------------------------
    def _normalize_label(self, lb: Any) -> Dict:
        """Make a label dict consistent"""
        if isinstance(lb, dict):
            return {
                "id": lb.get("id"),
                "type": lb.get("type"),
                "mass": lb.get("mass", 1),
                "coord": tuple(lb.get("coord", (0, 0))),
                "owner": lb.get("owner"),
            }
        # fallback for objects
        return {
            "id": getattr(lb, "id", None),
            "type": getattr(lb, "type", None),
            "mass": getattr(lb, "mass", 1),
            "coord": getattr(lb, "coord", (0, 0)),
            "owner": getattr(lb, "owner", None),
        }

    def _normalize_agent(self, ag: Any) -> Dict:
        if isinstance(ag, dict):
            return {
                "id": ag.get("id"),
                "type": ag.get("type"),
                "state": ag.get("state", {}),
                "coord": tuple(ag.get("coord", (0, 0))),
            }
        return {
            "id": getattr(ag, "id", None),
            "type": getattr(ag, "type", None),
            "state": getattr(ag, "state", {}),
            "coord": getattr(ag, "coord", (0, 0)),
        }

