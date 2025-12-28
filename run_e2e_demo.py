#!/usr/bin/env python3
# run_e2e_demo.py — end-to-end smoke demo for scan-master -> cell-master

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

    # step antigen so label is written
    ant.step(region_id='epi_1', rng=ant.rng, tick=1)

    # show space labels after ant step
    labels = s.get_labels('epi_1')
    print("\n[step] space labels after antigen step:")
    pp.pprint(labels)

    # aggregator -> receptor match -> nodes
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

    # node -> intents
    intents = []
    for n in nodes:
        intents.extend(map_node_to_intents(n))
    print("\n[intents] intents to execute:")
    pp.pprint(intents)

    # execute intents (should create mhc_pep_* and dc_presenting labels)
    events = execute_intents(s, region_id='epi_1', intents=intents)
    print("\n[execute] executor events:")
    pp.pprint(events)

    print("\n[space] labels after executor:")
    pp.pprint(s.get_labels('epi_1'))

    # now try T cell activation (use high recognition prob to force activation)
    act_events = activate_tcells(s, 'epi_1', rng=ant.rng, params={'recognition_prob': 0.95, 'il12_thresh': 0.0})
    print("\n[activate] tcell activation events:")
    pp.pprint(act_events)

    print("\n[final] final labels in space (summary):")
    final = s.get_labels('epi_1')
    pp.pprint(final)

    # quick checks
    ids = [l.get('id') for l in final]
    ok_ant = any(i and i.startswith('ant_label_') for i in ids)
    ok_mhc = any(i and i.startswith('mhc_pep_') for i in ids)
    ok_t = any(i and (i.startswith('t_activated_') or i.startswith('t_diff_') or i.startswith('t_tcr_')) for i in ids)

    print("\n[checks] ant_label present:", ok_ant, "mhc_pep present:", ok_mhc, "tcell labels present:", ok_t)
    if not (ok_ant and ok_mhc):
        print("-> 部分关键标签缺失，建议查看上面每一步的输出并按位置排查。")

if __name__ == '__main__':
    main()

