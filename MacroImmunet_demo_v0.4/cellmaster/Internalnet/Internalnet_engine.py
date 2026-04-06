import json
import os
from cellmaster.Internalnet.node_engine import run_node_graph, load_nodes
from cellmaster.Internalnet.HIR.hir_core import compute_HIR
from cellmaster.Internalnet.state.state_update import apply_state_update
from cellmaster.Internalnet.behavior_engine import evaluate_behaviors
from cellmaster.Internalnet.HIR.hir_features import build_hir_features
from cellmaster.Internalnet.node_engine import collect_emitters
from cellmaster.Internalnet.graph_loader import GraphLoader
class InternalNet:

    def __init__(self, behaviors):
        self.behaviors = behaviors
        self.node_defs = {n["node_id"]: n for n in load_nodes()}  # ✅ 缓存
        graph_dir = os.path.join(os.path.dirname(__file__), "graph", "defs")
        self.graph_loader = GraphLoader(graph_dir)

    # =========================
    # 🔹 node only
    # =========================
    def run_node_only(self, cell, external_field):
        graph = self.graph_loader.load(cell.graph)
        print("GRAPH CONFIG:", cell.graph)
        print("GRAPH NODES:", list(graph["nodes"].keys())[:5])

        node_state = cell.node_state
        
        # 🔥 拿到 update_order
        node_state, update_order = run_node_graph(
            node_state,
            graph,
            self.node_defs,
            external_field,
            receptor_params=cell.receptor_params
        )

        cell.node_state = node_state

        # =========================
        # 🔹 Debug 输出
        # =========================
        print(f"\n[{cell.cell_type}] --- Node State Snapshot ---")

        # receptors
        for r in ["TCR_receptor", "costim_receptor", "IFN_receptor"]:
            print(f"  [Receptor] {r}: {round(node_state.get(r, 0.0), 3)}")
 
        # signals
        for sig in ["activation_signal", "cytotoxic_program", "stress"]:
            print(f"  [Signal] {sig}: {round(node_state.get(sig, 0.0), 3)}")

        # 🔥 节点执行顺序
        print("  [Update Order]:")
        for node in update_order:
            print(f"    {node}")

        return update_order   # 🔥给 step 用（可选）
    # =========================
    # 🔹 behavior + fate
    # =========================
    def run_behavior_and_fate(self, cell, graph):

        node_state = cell.node_state
 
        features = build_hir_features(node_state, cell.feature_params)
        hir_output = compute_HIR(features, cell)

        behavior_outputs = evaluate_behaviors(
            node_state,
            hir_output,
            self.behaviors,
            cell=cell,
            graph=graph   # ✅ 正确
        )

        node_state = apply_state_update(
            node_state,
            behavior_outputs,
            self.node_defs   # 🔥 顺便修这个（后面讲）
        )

        cell.node_state = node_state

        return {
            "behaviors": behavior_outputs,
            "hir": hir_output,
            "fate": hir_output["fate"],
            "features": features
        }

    # =========================
    # 🔹 unified step
    # =========================
    def step(self, cell, external_field):

        before_state = cell.node_state.copy()

        # 🔥 1️⃣ load graph once
        graph = self.graph_loader.load(cell.graph)

        # 🔥 2️⃣ node update
        node_state, update_order = run_node_graph(
            cell.node_state,
            graph,
            self.node_defs,
            external_field,
            receptor_params=cell.receptor_params
        )
        cell.node_state = node_state

        # 🔥 3️⃣ behavior + fate（传 graph 本体）
        result = self.run_behavior_and_fate(cell, graph)

        after_state = cell.node_state

        # -------------------------
        # 3️⃣ Debug（结构化）
        # -------------------------
        print("\n===== InternalNet Step Debug =====")

        print("External field:", external_field)

        # 🔥 state diff（关键！）
        print("\n[State Changes]")
        for k in before_state:
            before = before_state.get(k, 0)
            after = after_state.get(k, 0)
            if abs(after - before) > 1e-6:
                print(f"  {k}: {round(before,3)} → {round(after,3)}")

        # 🔥 behaviors
        print(f"\n[{cell.cell_type}] behaviors:")
        for b in result["behaviors"]:
            print(f"  {b['behavior_id']} → {round(b['activation'], 3)}")

        # 🔥 fate
        print(f"[{cell.cell_type}] fate: {result['fate']}")

        # 🔥 node list（修复版）
        print("\n[Node Registry]")
        print(list(self.node_defs.keys()))

        return result
