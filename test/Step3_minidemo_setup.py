#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3 文件生成器：一次性生成以下 3 个模块
- cell_master/behavior_mapper.py
- cell_master/intent_executor.py
- cell_master/step3_driver.py

运行方式：
    PYTHONPATH=. python3 Step3_minidemo_setup.py

运行成功后，你可以安全删除本文件。
"""

import os
from textwrap import dedent

FILES = {
    "cell_master/behavior_mapper.py": dedent("""
        # -*- coding: utf-8 -*-
        \"\"\"
        behavior_mapper：把 nodes 映射为 behaviors，再映射为 intents。
        Demo 版本：只处理 ANTIGEN_EXPOSURE -> produce_cytokine
        \"\"\"

        def map_nodes_to_behaviors(nodes):
            behaviors = []
            for n in nodes:
                if n["node_type"] == "ANTIGEN_EXPOSURE":
                    behaviors.append({
                        "behavior": "produce_cytokine",
                        "cytokine": "IL6",
                        "amount": 1.0,
                        "coord": n["coord"]
                    })
            return behaviors


        def behaviors_to_intents(behaviors):
            intents = []
            for b in behaviors:
                if b["behavior"] == "produce_cytokine":
                    intents.append({
                        "intent_type": "EMIT_CYTOKINE",
                        "cytokine": b["cytokine"],
                        "amount": b["amount"],
                        "coord": b["coord"],
                    })
            return intents
    """),

    "cell_master/intent_executor.py": dedent("""
        # -*- coding: utf-8 -*-
        \"\"\"
        intent_executor：执行意图（写回 Space）
        Demo：将细胞因子写成 label
        \"\"\"

        from scan_master.space import Label

        def execute_intents(space, region_id, intents):
            for it in intents:
                if it["intent_type"] == "EMIT_CYTOKINE":
                    lab = Label(
                        name="CYTOKINE",
                        type="CYTOKINE",
                        meta={
                            "cytokine": it["cytokine"],
                            "amount": it["amount"],
                        }
                    )
                    space.add_label(region_id, lab)
    """),

    "cell_master/step3_driver.py": dedent("""
        # -*- coding: utf-8 -*-
        \"\"\"
        Step3 demo driver：串联整个流程。
        - AntigenMaster
        - aggregator
        - receptor registry
        - node_builder
        - behavior_mapper
        - intent_executor
        \"\"\"

        from scan_master.space import Space
        from cell_master.masters.antigen_master import AntigenMaster
        from scan_master.aggregator import LabelAggregator
        from scan_master.receptor_registry import match_receptors_from_summary
        from scan_master.node_builder import build_nodes_from_summary

        from cell_master.behavior_mapper import map_nodes_to_behaviors, behaviors_to_intents
        from cell_master.intent_executor import execute_intents

        def run_demo():
            s = Space()
            ant = AntigenMaster(space=s)
            agg = LabelAggregator()

            region = "epi_1"

            ant.spawn_agent(coord=(0,0), proto={
                "amount": 2.0,
                "epitopes": [{"seq": "PEP_TEST_123", "score": 1.0}],
                "origin": "test_injection",
                "type": "VIRUS"
            })

            for tick in range(1, 4):
                print(f"\\n===== TICK {tick} =====")

                # Step A：master 写 antigen
                ant.step(region_id=region, rng=ant.rng, tick=tick)

                labels = s.get_labels(region)
                print("labels:", [(l.get("name"), l.get("type"), l.meta) for l in labels])

                # Step B：聚合 ligand summary
                summary = agg.aggregate_labels(labels)
                print("summary:", summary)

                # Step C：受体匹配
                hits = match_receptors_from_summary(summary)
                print("receptor hits:", hits)

                # Step D：构建 nodes
                nodes = build_nodes_from_summary(summary, hits)
                print("nodes:", nodes)

                # Step E：node → behavior → intents
                behaviors = map_nodes_to_behaviors(nodes)
                intents = behaviors_to_intents(behaviors)
                print("intents:", intents)

                # Step F：执行 intents 并写回 Space
                execute_intents(s, region, intents)

            print("\\nDONE Step3 demo.")

        if __name__ == "__main__":
            run_demo()
    """),
}


def ensure_dir(path):
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def write_files():
    for path, content in FILES.items():
        ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] wrote {path}")


if __name__ == "__main__":
    write_files()
    print("\n🍀 All step3 files generated! 你可以安全删除本脚本。\n")

