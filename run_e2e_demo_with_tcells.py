#!/usr/bin/env python3
# run_e2e_demo_with_tcells.py — same as run_e2e_demo but forces a NAIVE_T to demonstrate activation

from scan_master.space import Space
from cell_master.masters.antigen_master import AntigenMaster
from scan_master.aggregator import LabelAggregator
from scan_master.receptor_registry import match_receptors_from_summary
from scan_master.node_builder import build_nodes_from_summary
from cell_master.behavior_mapper import map_node_to_intents
from cell_master.intent_executor import execute_intents
from cell_master.tcell_activation import activate_tcells
import pprint, time

pp = pprint.PrettyPrinter(indent=2)

def main():
    s = Space()
    ant = AntigenMaster(space=s)
    agg = LabelAggregator()

    print("[demo] spawn antigen")
    aid = ant.spawn_agent(coord=(0,0), proto={
        'amount': 2.0,
        'epitopes': [{'seq': 'PEP_TEST_123', 'score': 1.0}],
        'origin': 'e2e_demo',
        'type': 'VIRUS'
    })
    print("  agent id:", aid)

    ant.step(region_id='epi_1', rng=ant.rng, tick=1)
    labels = s.get_labels('epi_1')
    print("\n[step] space labels after antigen step:")
    pp.pprint(labels)

    aglist = agg.aggregate_labels(labels)
    print("\n[aggregate] aggregated ligands:")
    pp.pprint(aglist)

    hits = match_receptors_from_summary(aglist)
    print("\n[receptors] receptor hits:")
    pp.pprint(hits)

    nodes = build_nodes_from_summary(aglist, hits)
    print("\n[nodes] nodes built:")
    for n in nodes:
        print(" -", n.get('node_type'), "targets:", n.get('targets'))

    intents = []
    for n in nodes:
        intents.extend(map_node_to_intents(n))
    print("\n[intents] intents to execute:")
    pp.pprint(intents)

    events = execute_intents(s, region_id='epi_1', intents=intents)
    print("\n[execute] executor events:")
    pp.pprint(events)

    print("\n[space] labels after executor:")
    pp.pprint(s.get_labels('epi_1'))

    # ---- INSERT a NAIVE_T into space so activate_tcells has something to activate ----
    naive_label = {
        'id': 'naive_t_demo_1',
        'coord': (0.0, 0.0),
        'meta': {'type': 'NAIVE_T', 'created_tick': int(time.time())}
    }
    # write robustly using the space API — Space.add_label supports (region, label)
    try:
        s.add_label('epi_1', naive_label)
    except Exception:
        # fallback to internal storage if add_label signature differs
        if hasattr(s, "_local_labels"):
            s._local_labels.setdefault('epi_1', []).append(naive_label)
        elif hasattr(s, "labels"):
            s.labels.append(naive_label)

    print("\n[setup] inserted NAIVE_T label into space (id=naive_t_demo_1)")

    # now activate: high recognition_prob and low il12_thresh to force activation in demo
    act_events = activate_tcells(s, 'epi_1', rng=ant.rng, params={'recognition_prob': 1.0, 'il12_thresh': 0.0})
    print("\n[activate] tcell activation events:")
    pp.pprint(act_events)

    print("\n[final] final labels in space (summary):")
    final = s.get_labels('epi_1')
    pp.pprint(final)

    # checks
    ids = [l.get('id') for l in final]
    ok_ant = any(i and i.startswith('ant_label_') for i in ids)
    ok_mhc = any(i and i.startswith('mhc_pep_') for i in ids)
    ok_t = any(i and (i.startswith('t_activated_') or i.startswith('t_diff_') or i.startswith('t_tcr_')) for i in ids)

    print("\n[checks] ant_label present:", ok_ant, "mhc_pep present:", ok_mhc, "tcell labels present:", ok_t)
    if not ok_t:
        print("-> 没有生成 tcell 标签：请检查 activate_tcells 的参数或 pMHC 写回（上面有详细输出）。")

if __name__ == '__main__':
    main()

