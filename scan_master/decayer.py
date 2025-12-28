# scan_master/decayer.py
"""
Decayer for MacroImmunet_demo - centralised half-life authoritative version.

Key differences vs prior:
 - Decayer maintains a half_life_map (canonical/name -> half_life) that is
   populated at init from scan_master.label_names.LABEL_REGISTRY (if available).
 - API to override or set half-life at runtime: set_half_life / load_from_config.
 - Priority when deciding half-life for a label instance:
     1) label['meta']['half_life'] if present
     2) decayer.get_half_life(canonical)  (from half_life_map)
     3) decayer.global_default_half_life (if not None)
     4) None => treat as non-decaying
 - apply_to_region returns per-label details about which half-life was used (for debugging).
"""

from typing import Optional, Dict, Any
from copy import deepcopy

# Try to import label registry for initial seeding. If absent, we still work.
try:
    from .label_names import LABEL_REGISTRY, classify_label_item, get_label_meta
except Exception:
    LABEL_REGISTRY = {}
    def classify_label_item(x): return {"original": x, "canonical": str(x.get("name","")).upper(), "meta": {}}
    def get_label_meta(x): return None

class Decayer:
    def __init__(self, removal_threshold: float = 1e-6, min_half_life: float = 1e-6, global_default_half_life: Optional[float] = None):
        """
        :param removal_threshold: labels with mass < threshold after decay will be removed
        :param min_half_life: protect against zero/negative half_life values
        :param global_default_half_life: if set, used as fallback half-life (otherwise None -> non-decay)
        """
        self.removal_threshold = float(removal_threshold)
        self.min_half_life = float(min_half_life)
        self.global_default_half_life = None if global_default_half_life is None else float(global_default_half_life)

        # central map: canonical/name -> half_life (float)
        self.half_life_map: Dict[str, float] = {}
        # try seeding from LABEL_REGISTRY if available
        try:
            for k, meta in LABEL_REGISTRY.items():
                if isinstance(meta, dict):
                    hl = meta.get("half_life") or meta.get("default_half_life")
                    if hl is not None:
                        try:
                            v = float(hl)
                            if v > 0:
                                self.half_life_map[k] = v
                        except Exception:
                            pass
        except Exception:
            # silently ignore seeding issues
            pass

    # ---------------- API to manage half-life registry ----------------
    def set_half_life(self, name_or_canonical: str, half_life: float):
        """Set or override half-life for a given canonical/name."""
        try:
            v = float(half_life)
            if v <= 0:
                raise ValueError("half_life must be > 0")
            self.half_life_map[str(name_or_canonical).upper()] = v
        except Exception as e:
            raise

    def get_half_life(self, name_or_canonical: str) -> Optional[float]:
        """Return half-life for given canonical/name or None if not found."""
        if name_or_canonical is None:
            return None
        key = str(name_or_canonical).upper()
        if key in self.half_life_map:
            return float(self.half_life_map[key])
        # allow lookup by label meta via LABEL_REGISTRY if present
        try:
            meta = get_label_meta(key)
            if meta:
                hl = meta.get("half_life") or meta.get("default_half_life")
                if hl is not None:
                    try:
                        return float(hl)
                    except Exception:
                        pass
        except Exception:
            pass
        # fallback to global default (could still be None)
        return self.global_default_half_life

    def load_from_config(self, cfg: Dict[str, Any]):
        """
        Load half-life overrides from a dict-like config:
        e.g. {"IL12": 10, "PERFORIN_PULSE": 0.8, "global_default_half_life": 5}
        """
        if not cfg:
            return
        # optional global default
        if "global_default_half_life" in cfg:
            try:
                self.global_default_half_life = float(cfg["global_default_half_life"])
            except Exception:
                pass
        # per-label overrides
        for k, v in cfg.items():
            if k == "global_default_half_life":
                continue
            try:
                self.set_half_life(k, float(v))
            except Exception:
                # ignore bad entries
                pass

    # ---------------- internal helpers ----------------
    def _decay_mass(self, mass: float, dt: float, half_life: float) -> float:
        if dt <= 0:
            return mass
        if half_life < self.min_half_life:
            half_life = self.min_half_life
        factor = 0.5 ** (dt / half_life)
        return mass * factor

    def _determine_half_life_for_label(self, label: dict) -> Optional[float]:
        """
        Determine half-life used for label instance.
        Priority:
          1) label['meta']['half_life']
          2) self.get_half_life(canonical)
          3) self.global_default_half_life
          4) None -> no decay
        Returns (half_life_or_None, source_string)
        """
        meta = label.get("meta", {}) or {}
        if "half_life" in meta:
            try:
                v = float(meta["half_life"])
                if v > 0:
                    return v, "instance_meta"
            except Exception:
                pass

        # try canonical mapping via classification
        try:
            classified = classify_label_item(label)
            canonical = classified.get("canonical")
            hl = self.get_half_life(canonical)
            if hl is not None:
                return hl, "decayer_registry"
            # also try raw name
            hl2 = self.get_half_life(label.get("name"))
            if hl2 is not None:
                return hl2, "decayer_registry_name"
        except Exception:
            pass

        # fallback to global default
        if self.global_default_half_life is not None:
            return self.global_default_half_life, "global_default"

        # none -> non-decaying
        return None, "none"

    # ---------------- main API ----------------
    def apply_to_region(self, space, region_id: str, current_tick: int) -> dict:
        """
        Apply decay to all labels in a given region.
        Returns a summary dict:
          {
            'n_before':int, 'n_after':int, 'removed':int, 'decayed':int,
            'details': [ { 'id':..., 'name':..., 'orig_mass':..., 'new_mass':..., 'half_life':..., 'hl_source':... }, ... ]
          }
        """
        labels = space.get_labels(region_id)
        n_before = len(labels)
        decayed_count = 0
        removed_count = 0
        details = []

        live = space.get_labels(region_id)  # deepcopy as Space provides
        new_list = []

        for lab in live:
            mass = float(lab.get("mass", 0.0))
            created = int(lab.get("created_tick", current_tick))
            dt = max(0, int(current_tick) - created)

            hl_pair = self._determine_half_life_for_label(lab)
            if isinstance(hl_pair, tuple):
                half_life, src = hl_pair
            else:
                half_life, src = (hl_pair, "unknown")

            if half_life is None:
                new_mass = mass
            else:
                new_mass = self._decay_mass(mass, dt, float(half_life))
                if abs(new_mass - mass) > 1e-12:
                    decayed_count += 1

            # record detail before removal decision
            details.append({
                "id": lab.get("id"),
                "name": lab.get("name"),
                "orig_mass": mass,
                "new_mass": new_mass,
                "half_life": half_life,
                "hl_source": src,
                "created_tick": created,
                "dt": dt,
            })

            # removal logic
            if new_mass is None or new_mass <= self.removal_threshold or new_mass <= 0.0 or (mass > 0 and new_mass/mass < 1e-12):
                removed_count += 1
                # skip
            else:
                lab2 = dict(lab)
                lab2["mass"] = float(new_mass)
                new_list.append(lab2)

        # write back
        try:
            space.replace_labels(region_id, new_list)
        except Exception:
            space.clear_region(region_id)
            space.extend_labels(region_id, new_list)

        return {
            "n_before": n_before,
            "n_after": len(new_list),
            "removed": removed_count,
            "decayed": decayed_count,
            "details": details
        }

    def apply_to_all(self, space, current_tick: int) -> dict:
        out = {}
        for region in space.regions():
            out[region] = self.apply_to_region(space, region, current_tick)
        return out

