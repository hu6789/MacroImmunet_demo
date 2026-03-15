#!/usr/bin/env python3
"""
tools/gen_behavior_tests.py

Generate unit-test skeletons for each behavior YAML under behaviors/.
By default it does a dry-run and prints what would be created.
Use --write to actually write files. Use --force to overwrite existing tests.
"""

import argparse
from pathlib import Path
import textwrap

BEH_DIR = Path("behaviors")
OUT_DIR = Path("tests/unit")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE = """\
# Auto-generated test skeleton for behavior: {stem}
# Source YAML: behaviors/{yaml_name}
#
# TODO: replace assertions with behavior-specific expectations.
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv
from tests.cell_tests.common.receptor_stubs import make_receptor_stub

def test_{stem}_basic_runs():
    cfg = load_yaml_rel("behaviors/{yaml_name}")
    bh = instantiate_behavior_from_yaml("behaviors/{yaml_name}", cfg)

    env = FakeEnv()
    # ensure commonly used fields exist (adjust as necessary)
    try:
        env.add_field("IL2")
    except Exception:
        pass

    cell = SimpleCellMock(state="activated", position=(1,1))
    receptors = make_receptor_stub({{"IL2": 10.0}})

    # call one of standard methods if present
    if hasattr(bh, "execute"):
        actions = bh.execute(cell=cell, env=env, receptors=receptors)
    elif hasattr(bh, "act"):
        actions = bh.act(cell=cell, env=env, receptors=receptors)
    elif hasattr(bh, "run"):
        actions = bh.run(cell=cell, env=env, receptors=receptors)
    else:
        actions = []

    # Basic assertions: behavior should return list-like actions
    assert isinstance(actions, (list, tuple))
    # TODO: refine expectations below for this specific behavior
    # Example: assert any(a.get("name") == "proliferate" for a in actions)
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write test files instead of dry-run")
    ap.add_argument("--force", action="store_true", help="Overwrite existing test files")
    ap.add_argument("--filter", type=str, default="", help="Optional substring to filter behavior files")
    args = ap.parse_args()

    yamls = sorted([p for p in BEH_DIR.glob("*.yaml") if args.filter in p.name])
    if not yamls:
        print("No behavior YAML files found in 'behaviors/'.")
        return

    created = []
    for p in yamls:
        stem = p.stem
        out_name = f"test_behavior_{stem}.py"
        out_path = OUT_DIR / out_name
        content = TEMPLATE.format(stem=stem, yaml_name=p.name)
        if out_path.exists() and not args.force:
            print(f"SKIP (exists): {out_path}")
            continue
        print(f"{'WRITE' if args.write else 'DRY-RUN'} -> {out_path}")
        if args.write:
            out_path.write_text(textwrap.dedent(content))
            created.append(str(out_path))
    if created:
        print("Created files:")
        for c in created:
            print("  -", c)
    else:
        print("No files written. Run with --write to create files (use --force to overwrite).")

if __name__ == "__main__":
    main()

