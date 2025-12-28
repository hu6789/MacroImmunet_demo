import unittest
from scan_master.space import Space
from cell_master.masters.antigen_master import AntigenMaster
from scan_master.aggregator import LabelAggregator
from scan_master.node_builder import build_nodes_from_summary
from scan_master.receptor_registry import match_receptors_from_summary
from cell_master.behavior_mapper import map_node_to_intents
from cell_master.intent_executor import execute_intents


class TestStep4Activation(unittest.TestCase):

    def test_tcell_activation_pipeline(self):
        # === Setup ===
        s = Space()
        ant = AntigenMaster(space=s)
        agg = LabelAggregator()
        region = 'epi_1'

        # === Step 1：放入抗原 ===
        ant.spawn_agent(
            coord=(0, 0),
            proto={
                'amount': 2.0,
                'epitopes': [{'seq': 'PEP_X_001', 'score': 1.0}],
                'origin': 'test_injection',
                'type': 'VIRUS'
            }
        )

        # === Step 2：运行 antigen master ===
        ant.step(region_id=region, rng=ant.rng, tick=1)
        labels = s.get_labels(region)
        agg_list = agg.aggregate_labels(labels)

        # === Step 3：匹配 receptor、构建 nodes ===
        hits = match_receptors_from_summary(agg_list)
        nodes = build_nodes_from_summary(agg_list, hits)

        # === Step 4：node → intents ===
        all_intents = []
        for n in nodes:
            intents = map_node_to_intents(n)
            all_intents.extend(intents)

        # === Step 5：执行 intents ===
        events = execute_intents(s, region_id=region, intents=all_intents)

        # === Step 6：检查是否成功生成 MHC peptide 或激活信号 ===
        labels_after = s.get_labels(region)
        mhc_labels = [l for l in labels_after if l.get("meta", {}).get("type") == "MHC_PEPTIDE"]

        self.assertGreater(len(mhc_labels), 0, "Should create MHC peptide after phagocytosis")


if __name__ == '__main__':
    unittest.main()

