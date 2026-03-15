# tests/cell_tests/common/yaml_loader.py
"""
Lightweight YAML loader for tests.
- Assumes repo root is two levels up from this file.
- Exposes:
    load_yaml_file(relpath)
    load_cell_deps_from_template(cell_template_id)
    load_behavior(behavior_id)
"""
import os
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

def load_yaml_file(relpath):
    """
    Load a YAML file given repository-relative path like "cells/DendriticCell_v1.yaml".
    Raises FileNotFoundError if not present.
    """
    p = os.path.join(ROOT, relpath)
    with open(p, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_behavior(behavior_id):
    """
    Convenience: load behaviors/<behavior_id>.yaml if present.
    Returns dict or raises FileNotFoundError.
    """
    return load_yaml_file(f"behaviors/{behavior_id}.yaml")

def load_cell_deps_from_template(cell_template_id):
    """
    Given a cell template id like "DendriticCell_v1", attempt to load:
      - cells/<cell_template_id>.yaml
      - receptors listed in cell YAML under 'receptors' (if any) -> returns list of receptor dicts
      - behaviors listed under 'behaviors' (if any) -> returns dict mapping behavior_id -> behavior dict
    Returns tuple: (cell_yaml_dict, list_of_receptor_dicts, dict_of_behavior_dicts)
    Missing receptor/behavior files are skipped (caller should decide whether that's an error).
    """
    cell_rel = f"cells/{cell_template_id}.yaml"
    cell = load_yaml_file(cell_rel)
    receptors = []
    behaviors = {}

    # receptors: cell may list entries as dicts or simple refs; normalize
    for r in cell.get('receptors', []) or []:
        # r may be dict like { ref: 'TLR_generic_v1', instance_params: {...} } or string
        ref = None
        if isinstance(r, dict):
            ref = r.get('ref') or r.get('id')
        elif isinstance(r, str):
            ref = r
        if not ref:
            continue
        try:
            receptors.append(load_yaml_file(f"receptors/{ref}.yaml"))
        except FileNotFoundError:
            # skip missing receptor - test runner logs missing_receptors elsewhere
            continue

    # behaviors: cell may list behavior IDs
    for b in cell.get('behaviors', []) or []:
        # b may be dict with id or string
        bid = None
        if isinstance(b, dict):
            bid = b.get('id') or b.get('ref') or b.get('name')
        elif isinstance(b, str):
            bid = b
        if not bid:
            continue
        try:
            behaviors[bid] = load_yaml_file(f"behaviors/{bid}.yaml")
        except FileNotFoundError:
            # skip missing behavior - runner has fallbacks for some
            continue

    return cell, receptors, behaviors
