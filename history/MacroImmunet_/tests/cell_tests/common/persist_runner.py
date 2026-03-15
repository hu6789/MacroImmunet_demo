# tests/cell_tests/common/persist_runner.py
"""
persist_runner — thin wrapper around runner_utils.run_cell_once
to persist artifacts in a timestamped folder under tests/_artifacts/
and produce a human_summary.txt for quick inspection.

Usage:
  from tests.cell_tests.common.persist_runner import persist_run_from_config
  outdir, summary = persist_run_from_config(config_dict_or_path, behaviors_impl_map=None, outroot="tests/_artifacts")
"""
import os, json, time
from pathlib import Path
import yaml

from tests.cell_tests.common.runner_utils import run_cell_once

def _ensure_cfg(cfg_or_path):
    if isinstance(cfg_or_path, (str, Path)):
        p = Path(cfg_or_path)
        return yaml.safe_load(open(p, 'r', encoding='utf-8'))
    elif isinstance(cfg_or_path, dict):
        return cfg_or_path
    else:
        raise RuntimeError("cfg_or_path must be path or dict")

def datetime_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

def make_human_summary(summary, outdir, lines=200):
    """
    Create human_summary.txt showing summary JSON + head of events & timeseries.
    """
    out = Path(outdir) / "human_summary.txt"
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write("Run summary (json):\n")
        json.dump(summary, fh, indent=2)
        fh.write("\n\nEvents head:\n")
        evp = Path(summary.get('events',''))
        if evp.exists():
            with open(evp, 'r', encoding='utf-8') as fe:
                for i, ln in enumerate(fe):
                    if i >= 200: break
                    fh.write(ln)
        fh.write("\n\nTimeseries head:\n")
        tsp = Path(summary.get('timeseries',''))
        if tsp.exists():
            with open(tsp, 'r', encoding='utf-8') as ft:
                for i, ln in enumerate(ft):
                    if i >= 200: break
                    fh.write(ln)
    return str(out)

def persist_run_from_config(cfg_or_path, behaviors_impl_map=None, outroot="tests/_artifacts", run_tag=None):
    """
    cfg_or_path: dict or path to config.yaml for a single-cell test (same shape as tests/.../config.yaml)
    behaviors_impl_map: optional dict { behavior_id: callable } to override implementations (useful for stubs)
    outroot: root folder to store artifacts
    run_tag: optional short tag to append to dir name (e.g., "phago_v1")
    Returns: (outdir_path_str, summary_dict)
    """
    cfg = _ensure_cfg(cfg_or_path)
    ts = datetime_stamp()
    cell_template = cfg.get('cell_template_id', cfg.get('cell', 'cell_test'))
    tag = f"_{run_tag}" if run_tag else ""
    outdir = Path(outroot) / f"{cell_template}_run{tag}_{ts}"
    outdir = str(outdir)
    os.makedirs(outdir, exist_ok=True)

    # call existing runner
    summary = run_cell_once(cfg.get('cell_template_id', cell_template), cfg, outdir, behaviors_impl_map=behaviors_impl_map)
    # add run metadata
    summary['_run_tag'] = run_tag
    summary['_timestamp'] = ts
    # write human summary
    human = make_human_summary(summary, outdir)
    summary['_human_summary'] = human

    return outdir, summary

