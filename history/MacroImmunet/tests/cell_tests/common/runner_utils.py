# tests/cell_tests/common/runner_utils.py
import importlib, json, os, csv, copy
from pathlib import Path
from datetime import datetime
from tests.cell_tests.common.receptor_stubs import simple_receptor_bound_count, integrate_with_decay

ROOT = Path(__file__).resolve().parents[2]

def resolve_impl_callable(impl_spec):
    """
    impl_spec: dict with keys 'module' and 'function'
    returns callable or raises
    """
    if not impl_spec or not isinstance(impl_spec, dict):
        raise RuntimeError("implementation spec missing or invalid")
    mod = importlib.import_module(impl_spec['module'])
    fn = getattr(mod, impl_spec['function'])
    return fn

def merge_params(defaults, override):
    """
    Merge defaults and override dictionaries.
    - If override missing -> return copy of defaults
    - If values are dicts, do a shallow merge for that key.
    """
    out = dict(defaults or {})
    if not override:
        return out
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out.get(k))
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    return out

def dump_jsonl(lines, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for item in lines:
            f.write(json.dumps(item, default=str) + "\n")

def save_timeseries_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def datetime_safe_str():
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def run_cell_once(cell_template_id, config, output_dir, behaviors_impl_map=None):
    """
    Runs a single scenario for a given cell template.
    - cell_template_id: e.g. "DendriticCell_v1"
    - config: dict loaded from tests/.../config.yaml (see examples)
    - output_dir: path to write artifacts
    - behaviors_impl_map: optional dict mapping behavior_id -> callable override
    Returns summary dict.
    """
    from tests.cell_tests.common.fake_env import FakeEnv
    from tests.cell_tests.common.yaml_loader import load_cell_deps_from_template

    env = FakeEnv(grid_size=tuple(config.get('grid_size',(11,11))))
    coord = tuple(config.get('coord',(5,5)))
    ticks = config.get('runtime',{}).get('ticks', 50)
    params_override = config.get('params_override', {}) or {}
    enable_behaviors = config.get('enable_behaviors', [])

    # seed fields
    for fid, items in config.get('initial_fields', {}).items():
        for it in items:
            env.set_field_point(fid, tuple(it['coord']), it['value'])

    cell_template, receptors_yaml, behaviors_yaml = load_cell_deps_from_template(cell_template_id)
    # runtime cell dict
    cell = {'id': config.get('cell_id', f"{cell_template_id}_test"),
            'coord': coord}
    state_store = {}  # per-behavior / per-receptor state

    events_out = []
    intents_out = []
    timeseries = []

    # helper to call a behavior (either resolved impl or stub)
    def call_behavior(beh_id):
        # find yaml: prefer cached mapping, else attempt loader; do NOT bail out immediately so fallback can run
        beh_yaml = None
        if behaviors_yaml and beh_id in behaviors_yaml:
            beh_yaml = behaviors_yaml.get(beh_id)
        else:
            try:
                # try to load behavior YAML by id/name using yaml_loader
                from tests.cell_tests.common.yaml_loader import load_behavior
                beh_yaml = load_behavior(beh_id)
            except Exception:
                beh_yaml = None

        impl = (beh_yaml.get('implementation') if beh_yaml else None) or (beh_yaml.get('implementation_hint') if beh_yaml else None) or {}
        params = merge_params(beh_yaml.get('params', {}) if beh_yaml else {}, params_override.get(beh_id, {}))
        st = state_store.setdefault(beh_id, {})
        try:
            # prefer provided callable map
            if behaviors_impl_map and beh_id in behaviors_impl_map:
                fn = behaviors_impl_map[beh_id]
                fn(cell, env, env.tick, st, params, read_fields_fn=env.read_field, emit_intent_fn=env.emit_intent, log_fn=env.log_event)
            elif isinstance(impl, dict) and impl.get('module') and impl.get('function'):
                fn = resolve_impl_callable(impl)
                fn(cell, env, env.tick, st, params, read_fields_fn=env.read_field, emit_intent_fn=env.emit_intent, log_fn=env.log_event)
            else:
                # fallback: some common declarative behaviors can be lightly emulated here
                # phagocytose minimal
                if beh_id == 'phagocytose_v1':
                    field_value = env.read_field('Field_Antigen_Density', cell['coord'])
                    uptake = params.get('uptake_per_tick', 2)
                    max_cap = params.get('max_capacity', 5)
                    if field_value > 0 and cell.get('antigen_load',0) < max_cap:
                        consumed = min(uptake, max_cap - cell.get('antigen_load',0), field_value)
                        env.add_to_field('Field_Antigen_Density', cell['coord'], -consumed)
                        cell['antigen_load'] = cell.get('antigen_load',0) + consumed
                        env.emit_event('phagocytosed', {'cell_id': cell['id'], 'amount': consumed, 'tick': env.tick})
                elif beh_id == 'present_v1':
                    if cell.get('antigen_load',0) > 0:
                        cell.setdefault('present_list', []).append({'peptide_id':'auto', 'mhc_type':'MHC_II','affinity':0.5})
                        env.emit_event('pMHC_presented', {'presenter': cell['id'], 'count': len(cell['present_list']), 'tick': env.tick})
                        cell['antigen_load'] = max(0, cell['antigen_load'] - 1)
                elif beh_id == 'secrete_v1' or beh_id == 'secrete':
                    # expected params: molecule, rate_per_tick, duration_ticks (optional)
                    mol = params.get('molecule') or (params.get('payload',{}) or {}).get('molecule')
                    rate = params.get('rate_per_tick', 0.1)
                    if mol:
                        env.add_to_field(f"Field_{mol}", cell['coord'], rate)
                        env.emit_event('secreted', {'cell_id': cell['id'], 'molecule': mol, 'amount': rate, 'tick': env.tick})
                elif beh_id == 'move_toward_v1' or beh_id == 'move_toward':
                    # simple chemotaxis: look for best neighbor by given chemokine in payload or params
                    chem = (params.get('chemokine') or (params.get('payload',{}) or {}).get('chemokine'))
                    if chem:
                        best = env.find_best_neighbor_by_field_gradient(cell['coord'], chem, params.get('max_step_distance',1))
                        if best:
                            env.emit_intent('move', {'to': best, 'cell_id': cell['id']})
                elif beh_id == 'proliferate_v1' or beh_id == 'proliferate':
                    # schedule immediate simple spawn intent (runner does not spawn real cells here)
                    divisions = int(params.get('divisions', params.get('daughter_count', 1)))
                    env.emit_event('divided', {'cell_id': cell['id'], 'divisions': divisions, 'tick': env.tick})
                # add more light fallbacks as needed
        except Exception as e:
            env.log_event(env.tick, 'behavior_error', {'behavior': beh_id, 'error': repr(e)})
            raise

    # receptor runner (simple equilibrium + integral) - enhanced
    def run_receptors():
        for r_yaml in (receptors_yaml or []):
            rid = r_yaml.get('id') or r_yaml.get('name')
            if not rid:
                continue
            p = r_yaml.get('default_params', {})
            ligand_field = r_yaml.get('ligand_field')
            L = env.read_field(ligand_field, cell['coord']) if ligand_field else 0.0
            bound = simple_receptor_bound_count(L, p)
            st = state_store.setdefault(f"receptor::{rid}", {})
            st['integral'] = integrate_with_decay(st.get('integral',0.0), bound, p.get('integration_window_ticks',24))
            # if threshold crossed, trigger downstream behaviors
            trig = False
            try:
                trig = (bound >= float(p.get('activation_threshold_nbound', 1)) or st['integral'] >= float(p.get('activation_threshold_integral', 1e12)))
            except Exception:
                trig = (bound >= p.get('activation_threshold_nbound', 1))
            if trig:
                for downstream in r_yaml.get('downstream',{}).get('on_activation',[]):
                    bname = downstream.get('behavior')
                    payload = downstream.get('payload', {}) or {}
                    if bname:
                        # merge payload into params_override for that behavior during this run
                        saved = copy.deepcopy(params_override.get(bname)) if params_override.get(bname) else None
                        params_override.setdefault(bname, {})
                        for k,v in payload.items():
                            params_override[bname][k] = v
                        try:
                            call_behavior(bname)
                        finally:
                            if saved is None:
                                params_override.pop(bname, None)
                            else:
                                params_override[bname] = saved

    # main tick loop
    for t in range(ticks):
        env.tick = t
        # run receptors first (so their downstream behaviors may emit intents/events)
        run_receptors()
        # run enabled behaviors in config order
        for beh in enable_behaviors:
            call_behavior(beh)
        # record logs
        # collect some fields for timeseries (customize as needed)
        ts_row = {'tick': t,
                  'antigen_load': cell.get('antigen_load', 0),
                  'present_count': len(cell.get('present_list', [])),
                  'field_antigen': env.read_field('Field_Antigen_Density', cell['coord'])}
        # include receptor integrals if present
        for key,st in list(state_store.items()):
            if key.startswith("receptor::"):
                ts_row[key] = st.get('integral', 0.0)
        timeseries.append(ts_row)
        # snapshot events/intents
        for ev in list(env.events):
            events_out.append({'tick': ev[0], 'event': ev[1], 'payload': ev[2]})
        for it in list(env.intents):
            intents_out.append({'tick': it[0], 'intent': it[1], 'payload': it[2]})
        env.events.clear(); env.intents.clear()
        # advance env if it has step
        try:
            env.step()
        except Exception:
            env.tick += 1

    # write artifacts
    ts_path = os.path.join(output_dir, "timeseries.csv")
    events_path = os.path.join(output_dir, "events.jsonl")
    intents_path = os.path.join(output_dir, "intents.jsonl")
    summary_path = os.path.join(output_dir, "summary.json")
    save_timeseries_csv(timeseries, ts_path)
    dump_jsonl(events_out, events_path)
    dump_jsonl(intents_out, intents_path)
    summary = {
        'cell': cell_template_id,
        'ticks': ticks,
        'final_antigen_load': cell.get('antigen_load',0),
        'present_count': len(cell.get('present_list',[])),
        'timeseries': ts_path,
        'events': events_path,
        'intents': intents_path,
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    return summary
