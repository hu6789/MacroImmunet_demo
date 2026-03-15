#!/usr/bin/env python3
"""
Timeline runner for runner_ein scenarios.

Usage:
  PYTHONPATH=. python3 runner_ein/timeline_runner.py <scenario_path> [--ticks N] [--dump_json OUT]

Example:
  PYTHONPATH=. python3 runner_ein/timeline_runner.py runner_ein/scenarios/low_virus.yaml --ticks 20
"""

from typing import Any, Dict, List, Optional
import argparse
import json
import pprint
import traceback
import os
import gzip
import datetime
import subprocess
import sys

# import project loader + scheduler + percell
from runner_ein.loader import load_scenario
from runner_ein.percell.scheduler import Scheduler
# th2_percell is present, but we will dynamically import where needed
from runner_ein.percell import th2_percell  # keep available for demos


def _git_commit_hash() -> Optional[str]:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
            text=True,
        )
        return p.stdout.strip()
    except Exception:
        return None


def _auto_dump_timeline(timeline: Any, scenario_path: str, dump_json: Optional[str] = None,
                        out_dir: str = "runner_ein/results", compress: bool = True) -> str:
    """
    Write timeline to disk with metadata.

    Behavior:
      - ensure out_dir exists (default runner_ein/results)
      - if dump_json is None -> auto-name as <UTC>_<scenario_basename>.json.gz inside out_dir
      - if dump_json is provided:
          * if dump_json contains a directory part -> honor it (create dirs)
          * if dump_json is a plain filename (no dir) -> write into out_dir and
            append scenario basename + timestamp if that filename already exists to avoid silent overwrites
          * if dump_json endswith .json.gz -> treat as compressed output; if endswith .json -> compress to .json.gz
            (unless compress=False).
    Returns absolute path written.
    """
    os.makedirs(out_dir, exist_ok=True)

    meta = {
        "scenario": scenario_path,
        "cmd": " ".join(sys.argv),
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }
    commit = _git_commit_hash()
    if commit:
        meta["git_commit"] = commit

    wrapped = {"meta": meta, "timeline": timeline}

    # resolve scenario base name for friendly file names
    scenename = os.path.basename(scenario_path).replace(".yaml", "").replace(".yml", "")

    # helper to ensure we won't overwrite silently: if path exists, add timestamp suffix
    def _unique_path(path: str) -> str:
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        return f"{base}_{ts}{ext}"

    # if user provided dump_json
    if dump_json:
        # user may have provided a path like "dir/name.json" or just "name.json"
        provided_dir = os.path.dirname(dump_json)
        if provided_dir:
            # user gave a directory -> honor (create dir)
            target_dir = provided_dir
            os.makedirs(target_dir, exist_ok=True)
            fname = dump_json
            # if user provided .json.gz explicitly, keep compressed; if .json and compress True -> append .gz
            if compress and not fname.endswith(".gz"):
                if fname.endswith(".json"):
                    fname = fname + ".gz"
            # if user doesn't want compress, respect (compress flag false)
        else:
            # plain filename (no dir) -> write into out_dir to keep results together
            target_dir = out_dir
            os.makedirs(target_dir, exist_ok=True)
            # prefer to include scenario name if the user-provided filename is generic or reused.
            # If user supplied e.g. timeline_low_virus.json, keep that base but add scenename+timestamp if conflict.
            base_name = os.path.basename(dump_json)
            # if user ends with .json.gz keep it; if ends with .json and compress True -> will store .json.gz
            if compress and base_name.endswith(".json") and not base_name.endswith(".json.gz"):
                fname = base_name + ".gz"
            else:
                fname = base_name
            fname = os.path.join(target_dir, fname)
            # if target exists, append scenario and timestamp to avoid accidental overwrite
            if os.path.exists(fname):
                base, ext = os.path.splitext(fname)
                ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                fname = f"{base}_{scenename}_{ts}{ext}"

    else:
        # auto-name under out_dir: <UTC>_<scenename>.json.gz (or .json if compress False)
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        suffix = ".json.gz" if compress else ".json"
        fname = os.path.join(out_dir, f"{ts}_{scenename}{suffix}")

    # final write
    try:
        if compress:
            # ensure filename ends with .gz
            if not fname.endswith(".gz"):
                fname = fname + ".gz"
            with gzip.open(fname, "wt", encoding="utf-8") as f:
                json.dump(wrapped, f, indent=2, default=str)
        else:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(wrapped, f, indent=2, default=str)
    except Exception as e:
        # fallback plain write next to out_dir
        try:
            fallback = os.path.join(out_dir, f"timeline_fallback_{scenename}.json")
            with open(fallback, "w", encoding="utf-8") as f:
                json.dump(timeline, f, indent=2, default=str)
            return os.path.abspath(fallback)
        except Exception:
            raise e

    return os.path.abspath(fname)



def apply_master_intents(intents: List[Dict], space: Any, env: Any, scheduler: Scheduler, tm_params: Dict):
    """
    Apply simplistic handlers for demo intents:
      - attempt_infect -> reduce antigen_density / emit_event
      - deposit_cytokine -> update field
      - recruit_apc -> probabilistic spawn
      - tcr_activation/differentiate/proliferate -> emit events (or record)
      - percell_evaluate -> schedule with scheduler
    This is intentionally simple (demo-level).
    """
    applied = []
    for it in intents:
        try:
            action = it.get("action") or it.get("type")
            # infection attempt
            if action == "attempt_infect":
                coord = it.get("coord")
                x,y = coord
                if "Field_Antigen_Density" in space.fields:
                    try:
                        space.fields["Field_Antigen_Density"][y][x] = max(0.0, space.fields["Field_Antigen_Density"][y][x] - it.get("score",0.0)*0.5)
                    except Exception:
                        pass
                env.emit_event("attempt_infect", {"coord": coord, "strength": it.get("strength"), "score": it.get("score")})
                applied.append(("attempt_infect", it))

            elif action in ("deposit_cytokine", "deposit"):
                fld = it.get("field")
                coord = it.get("coord") or it.get("location")
                x,y = coord
                try:
                    space.fields.setdefault(fld, [[0.0]*space.w for _ in range(space.h)])
                    space.fields[fld][y][x] += float(it.get("amount", 0.0))
                except Exception:
                    pass
                env.emit_event("deposit", {"field": fld, "coord": coord, "amount": it.get("amount")})
                applied.append(("deposit", it))

            elif action in ("recruit_apc", "recruit"):
                prob = float(it.get("probability", it.get("prob", 0.5)))
                import random
                if random.random() <= prob:
                    env.emit_event("apc_spawned", {"coord": it.get("coord"), "cell_type": it.get("cell_type")})
                    applied.append(("recruit_apc_spawned", it))
                else:
                    env.emit_event("apc_recruit_skipped", {"coord": it.get("coord"), "prob": prob})
                    applied.append(("recruit_apc_skipped", it))

            elif action in ("tcr_activation",):
                env.emit_event("tcr_activation", {"cell_id": it.get("cell_id"), "affinity": it.get("best_affinity"), "pmhc": it.get("pmhc_summary")})
                applied.append(("tcr_activation", it))

            elif action in ("differentiate",):
                env.emit_event("differentiate", {"cell_id": it.get("cell_id"), "target_state": it.get("target_state"), "prob": it.get("probability")})
                applied.append(("differentiate", it))

            elif action in ("proliferate",):
                env.emit_event("proliferate", {"cell_id": it.get("cell_id"), "probability": it.get("probability")})
                applied.append(("proliferate", it))

            elif action in ("percell_evaluate","percell","percell_decide"):
                # schedule via scheduler respecting percell config if provided
                percell_conf = (tm_params.get("percell", {}) or {}).get(it.get("percell_type"), {})
                latency = int(percell_conf.get("decision_latency_ticks", 0))
                # schedule for later ticks (demo uses current_tick passed in intent if present)
                scheduler.submit(cell=None, intent=it, space=space, env=env,
                                 percell_type=it.get("percell_type"),
                                 latency_ticks=latency,
                                 current_tick=it.get("current_tick", getattr(env,"tick",0)),
                                 params=percell_conf or {},
                                 execute_immediately=False)
                applied.append(("percell_scheduled", it))

            else:
                # unknown action: just emit
                env.emit_event("master_intent", it)
                applied.append(("master_intent", it))

        except Exception as e:
            if env and hasattr(env, "emit_event"):
                env.emit_event("intent_apply_error", {"intent": it, "error": str(e), "trace": traceback.format_exc()})
    return applied


def run_timeline(scenario_path: str, ticks: int = 10, dump_json: Optional[str] = None):
    space, env, masters, cfg = load_scenario(scenario_path)
    scheduler = Scheduler(env=env)

    timeline = []
    # optionally include master params for percell scheduling hints (take from first relevant master)
    # find T master / naive master params if present
    tm_params = {}
    for m in masters:
        # try to pick up params attribute if exists
        try:
            if getattr(m, "params", None):
                # merge heuristically
                tm_params.update(m.params or {})
        except Exception:
            pass

    # run ticks
    for tick in range(ticks):
        env.tick = tick
        tick_entry = {"tick": tick, "events": [], "cell_changes": [], "field_summaries": {}}

        # 1) run masters
        all_intents = []
        for m in masters:
            try:
                intents = m.tick()
                if intents:
                    # stamp current_tick on intents so scheduling can use it
                    for it in intents:
                        it.setdefault("current_tick", tick)
                all_intents.extend(intents or [])
            except Exception as e:
                if hasattr(env, "emit_event"):
                    env.emit_event("master_tick_error", {"master": m.__class__.__name__, "error": str(e), "trace": traceback.format_exc()})

        # 2) simple application of master intents (demo-level)
        applied = apply_master_intents(all_intents, space, env, scheduler, tm_params)

        # 3) advance scheduler and execute due percell decisions
        due = scheduler.advance(tick)
        percell_actions = []
        for entry in due:
            cell = entry.get("cell")
            intent = entry.get("intent") or {}
            ptype = entry.get("percell_type")
            params = entry.get("params", {}) or {}
            # attempt to import module (use scheduler helper)
            try:
                per_mod, err = scheduler._import_percell_module(ptype)
                if per_mod is None:
                    if hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"module_import_failed","detail":err,"percell_type":ptype})
                    continue
                decide_fn = getattr(per_mod, "decide", None)
                if not callable(decide_fn):
                    if hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"no_decide_fn","percell_type":ptype})
                    continue
                # call decide
                try:
                    actions = decide_fn(cell, env, intent, params)
                except Exception as e:
                    if hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"decide_exception","percell_type":ptype,"cell_id": getattr(cell,"id",None), "error": str(e)})
                    actions = []
            except Exception as e:
                actions = []
                if hasattr(env, "emit_event"):
                    env.emit_event("percell_error", {"cell_id": getattr(cell,"id",None), "error": str(e), "trace": traceback.format_exc()})

            # normalize and apply action effects (demo)
            if actions is None:
                actions = []
            if isinstance(actions, dict):
                actions = [actions]
            for a in actions:
                # let env log the percell events (the percell module should already do this in many cases)
                name = a.get("name")
                payload = a.get("payload", {}) or {}
                # example: secrete IL4 -> update Field_IL4
                if name == "secrete":
                    sub = payload.get("substance")
                    amt = float(payload.get("amount", 1.0))
                    if sub and "Field_"+sub in space.fields:
                        try:
                            x,y = getattr(entry.get("cell"), "coord", (None,None))
                            if x is not None:
                                space.fields["Field_"+sub][y][x] += amt
                        except Exception:
                            pass
                if hasattr(env, "emit_event"):
                    env.emit_event(f"percell_action:{name}", {"cell_id": getattr(entry.get("cell"), "id", None), "action": a})
                percell_actions.append(a)

        # 4) collect human-friendly summary for this tick
        # take last N events from env.events (env likely appends events). We'll show the events generated during this tick.
        # We try to filter events by their tick-emission timing; env in loader/demo stores all events in 'env.events' as tuples (name,payload).
        # For simplicity, show last 50 events each tick and rely on chronological order.
        recent = env.events[-200:] if hasattr(env, "events") else []
        tick_entry["events"] = recent[:]  # copy for this demo

        # cell_changes: give minimal per-cell snapshot for cells that appeared/changed
        cell_changes = []
        try:
            for cid, c in getattr(space, "cells", {}).items():
                # show id, coord, type, basic meta
                try:
                    cell_changes.append({"id": cid, "coord": getattr(c, "coord", None), "type": getattr(c, "cell_type", getattr(c,"type",None)), "meta_keys": list(getattr(c,"meta",{}).keys())})
                except Exception:
                    pass
        except Exception:
            pass
        tick_entry["cell_changes"] = cell_changes

        # field_summaries: small summary for interested fields (antigen, IL12, IL4)
        def summary_field(field_name):
            try:
                fld = space.fields.get(field_name)
                if not fld:
                    return None
                # give small local view: sum, max, hotspots (coords)
                total = 0.0
                mx = -1.0
                hotspots = []
                for y,row in enumerate(fld):
                    for x,v in enumerate(row):
                        try:
                            fv = float(v)
                        except Exception:
                            fv = 0.0
                        total += fv
                        if fv > mx:
                            mx = fv
                            hotspots = [(x,y)]
                        elif fv == mx and fv > 0:
                            hotspots.append((x,y))
                return {"sum": total, "max": mx, "hotspots": hotspots[:5]}
            except Exception:
                return None

        tick_entry["field_summaries"]["Field_Antigen_Density"] = summary_field("Field_Antigen_Density")
        tick_entry["field_summaries"]["Field_IL12"] = summary_field("Field_IL12")
        tick_entry["field_summaries"]["Field_IL4"] = summary_field("Field_IL4")

        timeline.append(tick_entry)

    # print timeline human-friendly
    pp = pprint.PrettyPrinter(width=140, compact=False)
    for te in timeline:
        print("="*60)
        print(f"TICK {te['tick']}")
        print("- events (last few):")
        # print a short selection
        for e in te["events"][-12:]:
            print("  ", e)
        print("- cell snapshot (ids / coords / types):")
        for c in te["cell_changes"]:
            print("   ", c)
        print("- fields summary:")
        for k,v in te["field_summaries"].items():
            print("   ", k, ":", v)
        print()

    if dump_json:
        # If user provided a specific path, write to that (append .gz if needed)
        try:
            out_path = _auto_dump_timeline(timeline, scenario_path=scenario_path, dump_json=dump_json, compress=True)
            print(f"Timeline written to {out_path}")
        except Exception as e:
            print("Failed to write JSON (user path):", e)
    else:
        # default behavior: auto-write into runner_ein/results with metadata and gzip
        try:
            out_path = _auto_dump_timeline(timeline, scenario_path=scenario_path, dump_json=None, compress=True)
            print(f"Timeline written to {out_path}")
        except Exception as e:
            print("Failed to auto-write timeline:", e)

    return timeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", help="path to scenario yaml (loader.load_scenario compatible)")
    parser.add_argument("--ticks", "-n", type=int, default=8, help="number of ticks to simulate")
    parser.add_argument("--dump_json", help="optional path to write timeline as JSON (if omitted, auto-write to runner_ein/results/*.json.gz)")
    args = parser.parse_args()
    # store scenario_path for writer
    scenario_path = args.scenario
    run_timeline(args.scenario, ticks=args.ticks, dump_json=args.dump_json)

