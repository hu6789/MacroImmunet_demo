# scan_master/space.py
"""
Enhanced Space manager for MacroImmunet_demo (v2).

Features:
 - region-based label storage
 - agent registry: add_agent, move_agent, list_agents, remove_agent
 - snapshot / get_grid_summary
 - backward-compatible adapter wrappers (prints deprecation warnings)
 - best-effort fallbacks if shared.interfaces or scan_master.utils helpers are missing
"""

from typing import Dict, Any, List, Tuple, Optional
from copy import deepcopy
import uuid
import math
import threading
import logging
import warnings

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# try to import optional shared interfaces (for typing / optional stricter schema)
try:
    from shared.interfaces import Label, Agent, Snapshot, SnapshotRegion  # type: ignore
except Exception:
    # fallback simple aliases (for runtime only)
    Label = Dict[str, Any]  # type: ignore
    Agent = Dict[str, Any]  # type: ignore
    Snapshot = Dict[str, Any]  # type: ignore
    SnapshotRegion = Dict[str, Any]  # type: ignore

# best-effort import of utility helpers
try:
    from scan_master.utils import deprecation_warn, normalize_label_input  # type: ignore
except Exception:
    # fallback implementations
    def deprecation_warn(msg: str):
        warnings.warn(msg, DeprecationWarning)
    def normalize_label_input(label: Dict[str, Any]) -> Dict[str, Any]:
        # ensure common keys exist and normalize minimal shape
        if label is None:
            return {}
        l = dict(label)
        # older label might pass name in 'type'
        if "name" not in l and "type" in l:
            l["name"] = l.get("type")
        return l

# classification helper (best-effort import)
try:
    from .label_names import classify_label_item  # type: ignore
except Exception:
    def classify_label_item(raw):
        name = raw.get("name", "")
        return {"original": raw, "canonical": str(name).upper() if name is not None else None, "meta": {"type": "unknown"}}

RawLabel = Dict[str, Any]
Coord = Tuple[float, float]

# module-level lock to guarantee atomic claim/transfer operations in single-process demo
_space_claim_lock = threading.Lock()


class Space:
    def __init__(self):
        # region_id -> list[RawLabel]
        self._regions: Dict[str, List[RawLabel]] = {}
        # region_id -> agents mapping: agent_id -> agent dict
        self._agents: Dict[str, Dict[str, Agent]] = {}
        # hotspot registry per region
        self._hotspots: Dict[str, List[Dict[str, Any]]] = {}
        # owner bookkeeping
        self._owner_load: Dict[str, int] = {}
        self._owner_capacity: Dict[str, int] = {}
        self._owner_priority: Dict[str, float] = {}

    # ---------------- region helpers ----------------
    def ensure_region(self, region_id: str):
        if region_id not in self._regions:
            self._regions[region_id] = []
        if region_id not in self._hotspots:
            self._hotspots[region_id] = []
        if region_id not in self._agents:
            self._agents[region_id] = {}

    def regions(self) -> List[str]:
        return list(self._regions.keys())

    def _assign_id_if_missing(self, label: RawLabel) -> RawLabel:
        l = dict(label or {})
        if "id" not in l or l.get("id") is None:
            l["id"] = str(uuid.uuid4())
        l.setdefault("created_tick", 0)
        l.setdefault("mass", 1.0)
        l.setdefault("coord", None)
        l.setdefault("meta", {})
        l.setdefault("owner", None)
        l.setdefault("type", l.get("type", l.get("name")))
        # ensure name exists
        if "name" not in l:
            l["name"] = l.get("type")
        return l

    # ---------------- basic CRUD (labels) ----------------
    def get_labels(self, region_id: str) -> List[RawLabel]:
        """Return deep-copied labels list for region."""
        self.ensure_region(region_id)
        return deepcopy(self._regions[region_id])

    def add_label(self, region_id: str, label: RawLabel):
        """Canonical method used by other modules (Label must be dict-like)."""
        self.ensure_region(region_id)
        l_in = normalize_label_input(label) if label is not None else {}
        l = self._assign_id_if_missing(l_in)
        self._regions[region_id].append(l)

    def extend_labels(self, region_id: str, labels: List[RawLabel]):
        for lab in labels:
            self.add_label(region_id, lab)

    def replace_labels(self, region_id: str, labels: List[RawLabel]):
        self.ensure_region(region_id)
        self._regions[region_id] = [self._assign_id_if_missing(normalize_label_input(l)) for l in (labels or [])]

    def remove_label(self, region_id: str, label_id: str) -> bool:
        """Remove label by id; updates owner bookkeeping when needed."""
        self.ensure_region(region_id)
        with _space_claim_lock:
            for i, l in enumerate(self._regions[region_id]):
                if l.get("id") == label_id:
                    owner = l.get("owner")
                    if owner:
                        self._increment_owner_load(owner, -1)
                    del self._regions[region_id][i]
                    return True
        return False

    def pop_labels(self, region_id: str) -> List[RawLabel]:
        self.ensure_region(region_id)
        out = deepcopy(self._regions[region_id])
        self._regions[region_id] = []
        return out

    def clear_region(self, region_id: str):
        self.ensure_region(region_id)
        self._regions[region_id] = []
        self._hotspots[region_id] = []
        self._agents[region_id] = {}

    # ---------------- spatial queries ----------------
    def _distance(self, a: Coord, b: Coord) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def get_labels_in_radius(self, region_id: str, center: Coord, radius: float) -> List[RawLabel]:
        self.ensure_region(region_id)
        out: List[RawLabel] = []
        for l in self._regions[region_id]:
            c = l.get("coord")
            if c is None:
                continue
            if self._distance(center, c) <= radius:
                out.append(deepcopy(l))
        return out

    def get_labels_in_bbox(self, region_id: str, xmin: float, ymin: float, xmax: float, ymax: float) -> List[RawLabel]:
        self.ensure_region(region_id)
        out: List[RawLabel] = []
        for l in self._regions[region_id]:
            c = l.get("coord")
            if c is None:
                continue
            x, y = c
            if xmin <= x <= xmax and ymin <= y <= ymax:
                out.append(deepcopy(l))
        return out

    def get_labels_by_name(self, region_id: str, name: str) -> List[RawLabel]:
        self.ensure_region(region_id)
        return [deepcopy(l) for l in self._regions[region_id] if l.get("name") == name]

    def get_labels_by_canonical(self, region_id: str, canonical: str) -> List[RawLabel]:
        self.ensure_region(region_id)
        out = []
        for l in self._regions[region_id]:
            try:
                c = classify_label_item(l).get("canonical")
            except Exception:
                c = None
            if c == canonical:
                out.append(deepcopy(l))
        return out

    # ---------------- agents ----------------
    def add_agent(self, region_id: str, agent: Agent) -> str:
        """Register an agent in a region. Returns agent_id (string)."""
        self.ensure_region(region_id)
        a = dict(agent or {})
        if "id" not in a or a.get("id") is None:
            a["id"] = str(uuid.uuid4())
        a.setdefault("coord", None)
        a.setdefault("state", "idle")
        a.setdefault("proto", {})
        a.setdefault("meta", {})
        # keep region reference for potential legacy callers
        a.setdefault("region_id", region_id)
        self._agents[region_id][a["id"]] = a
        return a["id"]

    def move_agent(self, region_id: str, agent_id: str, coord: Coord) -> bool:
        """Move an agent within its region (or set coord)."""
        self.ensure_region(region_id)
        if agent_id not in self._agents[region_id]:
            return False
        self._agents[region_id][agent_id]["coord"] = coord
        return True

    def list_agents(self, region_id: str) -> List[Agent]:
        self.ensure_region(region_id)
        return [deepcopy(v) for v in self._agents[region_id].values()]

    def get_agent(self, region_id: str, agent_id: str) -> Optional[Agent]:
        self.ensure_region(region_id)
        a = self._agents[region_id].get(agent_id)
        return deepcopy(a) if a is not None else None

    def remove_agent(self, region_id: str, agent_id: str) -> bool:
        self.ensure_region(region_id)
        if agent_id in self._agents[region_id]:
            del self._agents[region_id][agent_id]
            return True
        return False

    # ---------------- ownership bookkeeping ----------------
    def set_owner_capacity(self, owner_id: str, capacity: Optional[int]):
        if capacity is None or capacity <= 0:
            self._owner_capacity.pop(owner_id, None)
        else:
            self._owner_capacity[owner_id] = int(capacity)

    def get_owner_capacity(self, owner_id: str) -> Optional[int]:
        return self._owner_capacity.get(owner_id)

    def get_owner_load(self, owner_id: str) -> int:
        return int(self._owner_load.get(owner_id, 0))

    def _increment_owner_load(self, owner_id: str, delta: int = 1):
        if delta == 0:
            return
        self._owner_load[owner_id] = self.get_owner_load(owner_id) + delta
        if self._owner_load[owner_id] <= 0:
            self._owner_load.pop(owner_id, None)

    def set_owner_priority(self, owner_id: str, priority: float):
        self._owner_priority[owner_id] = float(priority)

    def get_owner_priority(self, owner_id: str) -> float:
        return float(self._owner_priority.get(owner_id, 0.0))

    # ---------------- label claim / transfer APIs ----------------
    def claim_label(self, region_id: str, label_id: str, claimant: str, force: bool = False,
                    owner_priority: Optional[float] = None) -> bool:
        self.ensure_region(region_id)
        with _space_claim_lock:
            lab = next((l for l in self._regions[region_id] if l.get("id") == label_id), None)
            if lab is None:
                return False
            cur_owner = lab.get("owner")
            if cur_owner == claimant:
                return True
            cap = self.get_owner_capacity(claimant)
            load = self.get_owner_load(claimant)
            if cap is not None and load >= cap and not force:
                return False
            if not cur_owner:
                lab["owner"] = claimant
                lab.setdefault("meta", {})["owner_since_tick"] = lab.get("created_tick", 0)
                self._increment_owner_load(claimant, +1)
                return True
            if force:
                self._increment_owner_load(cur_owner, -1)
                lab["owner"] = claimant
                self._increment_owner_load(claimant, +1)
                return True
            if owner_priority is not None:
                prev_prio = self.get_owner_priority(cur_owner)
                if owner_priority > prev_prio:
                    self._increment_owner_load(cur_owner, -1)
                    lab["owner"] = claimant
                    self._increment_owner_load(claimant, +1)
                    return True
                else:
                    return False
            return False

    def claim_labels(self, region_id: str, label_ids: List[str], claimant: str, force: bool = False,
                     owner_priority: Optional[float] = None) -> Dict[str, Any]:
        claimed = []
        failed = []
        with _space_claim_lock:
            for lid in label_ids:
                ok = self.claim_label(region_id, lid, claimant, force=force, owner_priority=owner_priority)
                if ok:
                    claimed.append(lid)
                else:
                    failed.append(lid)
        return {"claimed": claimed, "failed": failed}

    def transfer_label(self, region_id: str, label_id: str, new_owner: str) -> bool:
        self.ensure_region(region_id)
        with _space_claim_lock:
            lab = next((l for l in self._regions[region_id] if l.get("id") == label_id), None)
            if not lab:
                return False
            old = lab.get("owner")
            if old == new_owner:
                return True
            if old:
                self._increment_owner_load(old, -1)
            lab["owner"] = new_owner
            self._increment_owner_load(new_owner, +1)
            return True

    def release_label(self, region_id: str, label_id: str, owner_id: Optional[str] = None) -> bool:
        self.ensure_region(region_id)
        with _space_claim_lock:
            lab = next((l for l in self._regions[region_id] if l.get("id") == label_id), None)
            if not lab:
                return False
            cur = lab.get("owner")
            if cur is None:
                return True
            if owner_id is not None and cur != owner_id:
                return False
            lab["owner"] = None
            self._increment_owner_load(cur, -1)
            return True

    # ---------------- hotspots ----------------
    def add_hotspot(self, region_id: str, center: Optional[Coord], created_tick: int, meta: Dict[str, Any] = None) -> str:
        self.ensure_region(region_id)
        hid = str(uuid.uuid4())
        rec = {"hotspot_id": hid, "center": center, "created_tick": created_tick, "meta": meta or {}}
        self._hotspots[region_id].append(rec)
        return hid

    def get_hotspots(self, region_id: str) -> List[Dict[str, Any]]:
        self.ensure_region(region_id)
        return deepcopy(self._hotspots[region_id])

    def clear_hotspots_older_than(self, region_id: str, cutoff_tick: int):
        self.ensure_region(region_id)
        self._hotspots[region_id] = [h for h in self._hotspots[region_id] if h.get("created_tick", 0) >= cutoff_tick]

    # ---------------- helpers ----------------
    def has_recent_label(self, region_id: str, label_name: str, cooldown_ticks: int, current_tick: int) -> bool:
        self.ensure_region(region_id)
        for l in self._regions[region_id]:
            if l.get("name") == label_name:
                created = int(l.get("created_tick", 0))
                if (current_tick - created) <= cooldown_ticks:
                    return True
        return False

    def summarize_region(self, region_id: str, current_tick: int) -> Dict[str, Any]:
        """Produce a small summary used by aggregator/scorer/triggers."""
        self.ensure_region(region_id)
        labels = self.get_labels(region_id)
        agg: Dict[str, Dict[str, Any]] = {}
        field_keys = ["IL12", "IL2", "IFNG", "TNF", "CCL21", "CXCL10"]
        local_field = {k: 0.0 for k in field_keys}
        num_mhc = 0
        num_damp = 0
        ages: List[int] = []
        recent_spill_mass = 0.0
        ownership_mass = 0.0

        for l in labels:
            try:
                classified = classify_label_item(l)
                can = classified.get("canonical")
            except Exception:
                can = l.get("name")
            mass = float(l.get("mass", 1.0))
            created = int(l.get("created_tick", 0))
            owner = l.get("owner", None)
            ages.append(max(0, current_tick - created))
            key = can if can is not None else l.get("name")
            agg.setdefault(key, {"ligand": key, "mass": 0.0, "freq": 0})
            agg[key]["mass"] += mass
            agg[key]["freq"] += 1
            if key in field_keys:
                local_field[key] += mass
            if key in ("MHC_I", "MHC_II"):
                num_mhc += 1
            if key == "DAMP":
                num_damp += 1
            if owner:
                ownership_mass += mass
            if l.get("meta", {}).get("source") == "spill" and (current_tick - created) <= 5:
                recent_spill_mass += mass

        total_mass = sum(v["mass"] for v in agg.values()) if agg else 0.0
        label_count = len(labels)
        if agg:
            dominant, dom_mass = max(((k, v["mass"]) for k, v in agg.items()), key=lambda x: x[1])
        else:
            dominant, dom_mass = (None, 0.0)
        spectrum = {
            "total_mass": total_mass,
            "label_count": label_count,
            "dominant_epitope": dominant,
            "dominant_mass": dom_mass,
            "epitope_diversity": len([k for k, v in agg.items() if v["mass"] > 0]),
            "young_mass": sum(float(l.get("mass", 1.0)) for l in labels if (current_tick - int(l.get("created_tick", 0))) <= 3),
            "recent_spill_mass": recent_spill_mass,
            "ownership_fraction": ownership_mass / (total_mass + 1e-12),
            "median_age": (sorted(ages)[len(ages) // 2] if ages else None),
            "num_mhc": num_mhc,
            "num_damp": num_damp
        }
        ligand_summary = list(agg.values())
        return {"ligand_summary": ligand_summary, "spectrum": spectrum, "local_field": local_field}

    def get_grid_summary(self, region_id: str, current_tick: int = 0) -> Dict[str, Any]:
        """Alias for summarize_region (keeps naming used by other modules)."""
        return self.summarize_region(region_id, current_tick=current_tick)

    # ---------------- snapshot ----------------
    def snapshot(self) -> Snapshot:
        """Return a stable snapshot dict of the entire world (all regions)."""
        out: Snapshot = {"grid": None, "regions": {}, "owners": {}}
        for region in self.regions():
            labels = self.get_labels(region)  # deepcopy
            agents = self.list_agents(region)
            hotspots = self.get_hotspots(region)
            summary = self.summarize_region(region, current_tick=0)
            out["regions"][region] = {
                "labels": labels,
                "agents": agents,
                "hotspots": hotspots,
                "summary": summary
            }
        out["owners"] = {k: int(v) for k, v in self._owner_load.items()}
        return out

    # ---------------- backward-compatible adapter helpers ----------------
    # These helpers allow code calling old-style methods to still work

    def write_label(self, *args, **kwargs):
        """
        Backward-compatible write_label:
        Accepts:
          - write_label(region_id, label_dict)
          - write_label(label_dict)  (label must contain meta.origin_region or meta.region or meta.origin_agent_id)
        Will try to determine target region and call add_label(region_id, label).
        If region cannot be determined, will write into a special fallback region 'unknown_region'
        while emitting a deprecation warning.
        """
        # signatures:
        # 1) (region_id, label)
        # 2) (label,)
        region_id = None
        label = None

        if len(args) == 2:
            region_id, label = args[0], args[1]
        elif len(args) == 1:
            label = args[0]
            # try to extract region from label fields
            if isinstance(label, dict):
                # common places where region might be encoded
                region_id = label.get("region") or label.get("meta", {}).get("region") or label.get("meta", {}).get("origin_region")
        else:
            # fallback to kwargs
            region_id = kwargs.get("region_id", None)
            label = kwargs.get("label", None)

        if label is None:
            deprecation_warn("Space.write_label called with no label argument.")
            return None

        # if still no region, try to infer from origin_agent_id -> find agent's region
        if not region_id and isinstance(label, dict):
            origin_agent = label.get("meta", {}).get("origin_agent_id") or label.get("origin_agent_id")
            if origin_agent:
                # find the agent across regions
                for rid, agents_map in self._agents.items():
                    if origin_agent in agents_map:
                        region_id = rid
                        break

        if not region_id:
            deprecation_warn(
                "Space.write_label: couldn't infer region_id; writing to fallback region 'unknown_region'. "
                "Please upgrade callers to use add_label(region_id, label) or include meta.origin_region in label."
            )
            region_id = "unknown_region"

        # Normalize label and add
        try:
            lnorm = normalize_label_input(label) if label is not None else {}
        except Exception:
            lnorm = dict(label) if isinstance(label, dict) else {"name": str(label)}
        self.ensure_region(region_id)
        l = self._assign_id_if_missing(lnorm)
        # if label has owner bookkeeping info, don't clobber it here
        self._regions[region_id].append(l)
        return l.get("id")

    def add_to_region(self, region_id: str, label: RawLabel):
        deprecation_warn("Space.add_to_region is deprecated; use add_label(region_id,label).")
        self.add_label(region_id, label)

    # Old-style agent helpers some masters may call (keep for compatibility)
    def get_agents(self, region_id: Optional[str] = None) -> List[Agent]:
        """
        Backward-compatible get_agents:
         - get_agents() -> all agents across regions (legacy)
         - get_agents(region_id) -> agents in region
        """
        if region_id is None:
            # flatten all agents
            all_agents: List[Agent] = []
            for rid in list(self._agents.keys()):
                all_agents.extend([deepcopy(a) for a in self._agents[rid].values()])
            deprecation_warn("Space.get_agents() is deprecated; use list_agents(region_id) or list_agents for specific region.")
            return all_agents
        deprecation_warn("Space.get_agents(region_id) is deprecated; use list_agents(region_id).")
        return self.list_agents(region_id)

    def spawn_agent(self, region_id: str, agent: Agent) -> str:
        """Alias for older masters that call spawn_agent(region, agent_proto)."""
        deprecation_warn("Space.spawn_agent is deprecated; use add_agent(region_id, agent) instead.")
        return self.add_agent(region_id, agent)

    def remove_agent_legacy(self, agent_id: str) -> bool:
        """Legacy remove by id across regions (some masters called remove_agent(agent_id) without region)."""
        for rid in list(self._agents.keys()):
            if agent_id in self._agents[rid]:
                del self._agents[rid][agent_id]
                return True
        return False

    # convenience backwards aliases (short-term)
    addLabel = add_label
    getLabels = get_labels
    listAgents = list_agents
    spawnAgent = spawn_agent
    getAgents = get_agents
    removeAgentLegacy = remove_agent_legacy

# End of file

