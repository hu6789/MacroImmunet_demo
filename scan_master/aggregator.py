# scan_master/aggregator.py - LabelAggregator (SpaceAdapter-friendly)
import math
import statistics
import typing as _t
from typing import List, Dict, Any, Optional

from .label_names import classify_label_item, FIELD_LABELS, get_label_meta

# try to import SpaceAdapter if present; adapter is preferred when available
try:
    from .space_adapter import SpaceAdapter  # type: ignore
except Exception:
    SpaceAdapter = None  # type: ignore


class LabelAggregator:
    def __init__(self, cfg: Dict = None):
        self.cfg = cfg or {}
        # thresholds
        self.young_thresh = self.cfg.get('young_thresh', 3)
        self.recent_spill_window = self.cfg.get('recent_spill_window', 5)
        # list of fields we consider for local_field (can be extended)
        self.field_keys = self.cfg.get('field_keys', ["IL12", "IL2", "IFNG", "TNF", "CCL21", "CXCL10"])

    # -------------------------
    # Core: keep raw-label based APIs for backward compatibility
    # -------------------------
    def aggregate_labels(self, raw_labels: List[Dict[str, Any]], radius=1) -> List[Dict[str, Any]]:
        """
        Aggregate a list of *raw label dicts* into canonical ligand summary:
          [{'ligand': canonical_name, 'mass': total_mass, 'freq': count}, ...]
        This function is intentionally permissive about input label shape.
        """
        if not raw_labels:
            return []

        classified = [classify_label_item(r) for r in raw_labels]
        visible = [c for c in classified if c.get('meta', {}).get('visible_to_scan', True)]
        agg: Dict[str, Dict[str, Any]] = {}
        for c in visible:
            key = c.get('canonical') or c.get('original', {}).get('type') or "UNKNOWN"
            try:
                mass = float(c.get('original', {}).get('mass', 1.0))
            except Exception:
                mass = 1.0
            entry = agg.setdefault(key, {'ligand': key, 'mass': 0.0, 'freq': 0})
            entry['mass'] += mass
            entry['freq'] += 1
        return list(agg.values())

    def get_spectrum(self, raw_labels: List[Dict[str, Any]], current_tick: int, radius=1) -> Dict[str, Any]:
        """
        Produce a diagnostic spectrum summary from raw labels. Keeps behavior of the older implementation.
        """
        classified = [classify_label_item(r) for r in (raw_labels or [])]
        visible = [c for c in classified if c.get('meta', {}).get('visible_to_scan', True)]
        masses_by_canonical: Dict[str, float] = {}
        ages: List[int] = []
        recent_spill_mass = 0.0
        ownership_mass = 0.0
        num_mhc = 0
        num_damp = 0

        for c in visible:
            orig = c.get('original', {}) or {}
            can = c.get('canonical') or orig.get('type') or "UNKNOWN"
            try:
                mass = float(orig.get('mass', 1.0))
            except Exception:
                mass = 1.0
            created = int(orig.get('created_tick', current_tick))
            owner = orig.get('owner', None)

            masses_by_canonical.setdefault(can, 0.0)
            masses_by_canonical[can] += mass
            ages.append(max(0, current_tick - created))

            if (current_tick - created) <= self.recent_spill_window and orig.get('meta', {}).get('source') == 'spill':
                recent_spill_mass += mass

            if owner:
                ownership_mass += mass

            if can in ('MHC_I', 'MHC_II', 'MHC_PEPTIDE'):
                num_mhc += 1
            if can == 'DAMP' or can == 'PAMP_FRAG':
                num_damp += 1

        total_mass = sum(masses_by_canonical.values()) if masses_by_canonical else 0.0
        label_count = len(visible)
        if masses_by_canonical:
            # choose dominant by mass
            dominant, dominant_mass = max(masses_by_canonical.items(), key=lambda x: x[1])
        else:
            dominant, dominant_mass = (None, 0.0)

        epitope_diversity = len([k for k, v in masses_by_canonical.items() if v > 0])

        young_mass = 0.0
        for c in visible:
            orig = c.get('original', {}) or {}
            created = int(orig.get('created_tick', current_tick))
            age = max(0, current_tick - created)
            if age <= self.young_thresh:
                try:
                    young_mass += float(orig.get('mass', 1.0))
                except Exception:
                    young_mass += 1.0

        median_age = statistics.median(ages) if ages else None
        ownership_fraction = ownership_mass / (total_mass + 1e-12)

        local_field: Dict[str, float] = {}
        for f in self.field_keys:
            local_field[f] = masses_by_canonical.get(f, 0.0)

        spectrum = {
            "total_mass": total_mass,
            "label_count": label_count,
            "dominant_epitope": dominant,
            "dominant_mass": dominant_mass,
            "epitope_diversity": epitope_diversity,
            "young_mass": young_mass,
            "recent_spill_mass": recent_spill_mass,
            "ownership_fraction": ownership_fraction,
            "median_age": median_age,
            "num_mhc": num_mhc,
            "num_damp": num_damp,
            "local_field": local_field
        }
        return spectrum

    # -------------------------
    # SpaceAdapter-friendly helpers (new)
    # -------------------------
    def _wrap_space(self, space_obj: Any) -> Any:
        """
        If a SpaceAdapter is available and space_obj is not already an adapter, wrap it.
        Otherwise return space_obj unchanged.
        """
        if SpaceAdapter is None:
            # adapter not present in this environment; return raw
            return space_obj
        # if it's already an adapter (duck-typing)
        if getattr(space_obj, "list_labels", None) and getattr(space_obj, "get_grid_summary", None):
            return space_obj
        # else wrap
        try:
            return SpaceAdapter(space_obj)
        except Exception:
            # fallback: return original object
            return space_obj

    def aggregate_region(self, space: Any, region_id: str, radius: int = 1) -> List[Dict[str, Any]]:
        """
        Convenience: aggregate labels for a region given a space-like object.
        space can be a raw Space instance or a SpaceAdapter; this will try to wrap it.
        Returns the same structure as aggregate_labels (ligand summary list).
        """
        adapter = self._wrap_space(space)
        # try adapter.list_labels(region_id) first; if not available, try old APIs
        labels = None
        try:
            if hasattr(adapter, "list_labels"):
                labels = adapter.list_labels(region_id)
            elif hasattr(space, "get_labels"):
                labels = space.get_labels(region_id)
            elif hasattr(space, "_local_labels"):
                # best-effort: try _local_labels dict or list
                ll = getattr(space, "_local_labels")
                if isinstance(ll, dict):
                    labels = ll.get(region_id, [])
                elif isinstance(ll, list):
                    labels = ll
            elif hasattr(space, "labels"):
                labels = getattr(space, "labels")
        except Exception:
            labels = None

        if labels is None:
            labels = []

        return self.aggregate_labels(labels, radius=radius)

    def spectrum_region(self, space: Any, region_id: str, current_tick: Optional[int] = None, radius: int = 1) -> Dict[str, Any]:
        """
        Convenience: produce spectrum for a region. current_tick defaults to int(time.time()) if None.
        """
        import time
        if current_tick is None:
            current_tick = int(time.time())

        adapter = self._wrap_space(space)
        labels = None
        try:
            if hasattr(adapter, "list_labels"):
                labels = adapter.list_labels(region_id)
            elif hasattr(space, "get_labels"):
                labels = space.get_labels(region_id)
            else:
                labels = []
        except Exception:
            labels = []

        return self.get_spectrum(labels, current_tick=current_tick, radius=radius)


# -------------------------
# module-level convenience API
# -------------------------
_default_aggregator: Optional[LabelAggregator] = None


def get_default_aggregator(cfg: Dict = None) -> LabelAggregator:
    global _default_aggregator
    if _default_aggregator is None:
        _default_aggregator = LabelAggregator(cfg=cfg)
    return _default_aggregator


# -------------------------
# quick smoke test when run directly
# -------------------------
if __name__ == "__main__":
    # sample raw label shapes (varied to test robustness)
    raw = [
        {"id": "L1", "type": "ANTIGEN_PARTICLE", "mass": 2, "coord": (1, 2), "meta": {"created_tick": 0}},
        {"id": "L2", "type": "DEBRIS", "mass": 1, "coord": (1, 2), "meta": {"created_tick": 0}},
        {"id": "L3", "type": "IL12", "mass": 0.5, "coord": (1, 2), "meta": {"created_tick": 0}},
        {"id": "L4", "type": "CXCL10", "mass": 3.0, "coord": (2, 2), "meta": {"created_tick": 0}},
        # a label that looks like SpaceAdapter-normalized dict (to test classify_label_item tolerance)
        {"id": "L5", "name": "ANTIGEN_PARTICLE", "type": "ANTIGEN_PARTICLE", "mass": 1.0, "coord": (0, 0), "meta": {"visible_to_scan": True, "created_tick": 0}}
    ]
    agg = LabelAggregator()
    print("aggregate_labels:", agg.aggregate_labels(raw))
    print("spectrum:", agg.get_spectrum(raw, current_tick=10))

class ScanAggregator:
    """
    Consume grid_summary and emit node requests (hotspot-level).
    """
    def __init__(self, antigen_threshold: float = 1.0):
        self.antigen_threshold = antigen_threshold

    def build_nodes(self, grid_summary: Dict) -> List[Dict]:
        nodes = []

        for coord, cell in grid_summary.items():
            labels = cell.get("labels", {})
            antigen = labels.get("ANTIGEN", 0.0)

            if antigen >= self.antigen_threshold:
                nodes.append({
                    "behavior": "antigen_release",
                    "meta": {
                        "coord": coord,
                        "antigen": antigen
                    }
                })

        return nodes

