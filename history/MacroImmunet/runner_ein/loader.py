# runner_ein/loader.py
"""
Loader for runner_ein scenarios.

Exposes:
  load_yaml(path) -> dict
  load_scenario(path) -> (space, env, masters, cfg)

Behavior:
 - Reads YAML scenario, seeds space fields, builds EnvAdapter (from orchestrator_demo),
   and instantiates masters according to cfg['masters'] and per-master params.
 - Optionally imports AntigenMaster if runner_ein.masters.antigen_master exists and
   cfg contains 'antigen_master' section.
"""
import os
import yaml
import random
from typing import Tuple, List, Any, Dict, Optional

# Reuse FakeSpace and EnvAdapter from orchestrator_demo for simple demos
from runner_ein.orchestrator_demo import FakeSpace, EnvAdapter

# Standard masters (import defensively so loader doesn't crash if a module is missing)
try:
    from runner_ein.masters.epithelial_master import EpithelialMaster
except Exception:
    EpithelialMaster = None

try:
    from runner_ein.masters.dc_master import DCMaster
except Exception:
    DCMaster = None

try:
    from runner_ein.masters.naive_tcell_master import NaiveTCellMaster
except Exception:
    NaiveTCellMaster = None

try:
    from runner_ein.masters.th1_master import Th1Master
except Exception:
    Th1Master = None

# optional AntigenMaster (user-added)
try:
    from runner_ein.masters.antigen_master import AntigenMaster
except Exception:
    AntigenMaster = None


def load_yaml(path: str) -> Dict:
    """Load YAML from path (safe_load)."""
    with open(path, "r") as fh:
        return yaml.safe_load(fh) or {}


def build_space(cfg_space: Optional[Dict]) -> FakeSpace:
    """Create FakeSpace from cfg_space section."""
    cfg_space = cfg_space or {}
    w = int(cfg_space.get("w", 12))
    h = int(cfg_space.get("h", 6))
    space_id = cfg_space.get("space_id", "Lung_Tissue_2D")
    space = FakeSpace(space_id, w=w, h=h)

    # ensure common fields exist (antigen, debris, cytokines) to avoid KeyErrors later
    for fld in ("Field_Antigen_Density", "Field_Cell_Debris", "Field_IL12", "Field_IL4", "Field_CCL19"):
        if fld not in space.fields:
            space.fields[fld] = [[0.0 for _ in range(w)] for __ in range(h)]

    # seed fields from cfg
    for s in cfg_space.get("seed", []):
        field = s.get("field")
        coord = s.get("coord", [0, 0])
        x, y = int(coord[0]), int(coord[1])
        val = float(s.get("value", 0.0))
        if field not in space.fields:
            space.fields[field] = [[0.0 for _ in range(w)] for __ in range(h)]
        # safe write (within bounds)
        if 0 <= x < w and 0 <= y < h:
            space.fields[field][y][x] = val

    return space


def build_env() -> EnvAdapter:
    """Return an EnvAdapter instance for demo logging/events."""
    return EnvAdapter()


def build_masters(space: Any, env: Any, masters_cfg: Optional[Dict]) -> List[Any]:
    """
    Instantiate masters based on masters_cfg. masters_cfg should be a dict with flags and
    per-master params, e.g.:

    masters:
      epithelial: True
      epithelial_params: { ... }
      dc: True
      dc_params: { ... }
      antigen_master: { ... }   # if present, will be passed to AntigenMaster
    """
    masters_cfg = masters_cfg or {}
    masters: List[Any] = []

    # Antigen master (optional) - place early so antigen exists for epithelial scanning
    ag_cfg = masters_cfg.get("antigen_master", None)
    if AntigenMaster and ag_cfg is not None:
        try:
            am = AntigenMaster(space, env, params=ag_cfg)
            masters.append(am)
        except Exception as e:
            # don't crash loader; emit a lightweight event if env supports it
            try:
                env.emit_event("loader_warning", {"msg": "failed to instantiate AntigenMaster", "error": str(e)})
            except Exception:
                pass

    # Epithelial
    if masters_cfg.get("epithelial", True) and EpithelialMaster is not None:
        try:
            em_params = masters_cfg.get("epithelial_params", {}) or {}
            em = EpithelialMaster(space, env, params=em_params)
            masters.append(em)
        except Exception as e:
            try:
                env.emit_event("loader_warning", {"msg": "failed to instantiate EpithelialMaster", "error": str(e)})
            except Exception:
                pass

    # Dendritic cell master
    if masters_cfg.get("dc", True) and DCMaster is not None:
        try:
            dm_params = masters_cfg.get("dc_params", {}) or {}
            dm = DCMaster(space, env, params=dm_params)
            masters.append(dm)
        except Exception as e:
            try:
                env.emit_event("loader_warning", {"msg": "failed to instantiate DCMaster", "error": str(e)})
            except Exception:
                pass

    # Naive T cell master (CD4/CD8 naive scanning)
    if masters_cfg.get("naive_tcell", True) and NaiveTCellMaster is not None:
        try:
            tm_params = masters_cfg.get("naive_tcell_params", {}) or {}
            tm = NaiveTCellMaster(space, env, params=tm_params)
            masters.append(tm)
        except Exception as e:
            try:
                env.emit_event("loader_warning", {"msg": "failed to instantiate NaiveTCellMaster", "error": str(e)})
            except Exception:
                pass

    # Th1 master (optional)
    if masters_cfg.get("th1_master", False) and Th1Master is not None:
        try:
            th1_params = masters_cfg.get("th1_params", {}) or {}
            th1 = Th1Master(space, env, params=th1_params)
            masters.append(th1)
        except Exception as e:
            try:
                env.emit_event("loader_warning", {"msg": "failed to instantiate Th1Master", "error": str(e)})
            except Exception:
                pass

    return masters


def load_scenario(path: str) -> Tuple[Any, Any, List[Any], Dict]:
    """
    Load a scenario YAML and build (space, env, masters, cfg).
    Usage:
      space, env, masters, cfg = load_scenario("runner_ein/scenarios/low_dose.yaml")
    """
    cfg = load_yaml(path)
    seed = cfg.get("random_seed", None)
    if seed is not None:
        try:
            random.seed(int(seed))
        except Exception:
            pass

    # build space & env
    space = build_space(cfg.get("space", {}))
    env = build_env()

    # build masters (cfg section 'masters')
    masters_cfg = cfg.get("masters", {}) or {}
    masters = build_masters(space, env, masters_cfg)

    # emit a small load event if possible
    try:
        if hasattr(env, "emit_event"):
            env.emit_event("scenario_loaded", {"scenario": os.path.basename(path), "n_masters": len(masters)})
    except Exception:
        pass

    return space, env, masters, cfg

