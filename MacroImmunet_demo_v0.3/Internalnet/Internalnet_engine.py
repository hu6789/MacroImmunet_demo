import json
import os
import math

from Internalnet.node_engine import run_node_graph
from Internalnet.HIR.hir_core import compute_HIR
from Internalnet.state.state_update import apply_state_update
from Internalnet.behavior_engine import evaluate_behaviors
from Internalnet.HIR.hir_features import build_hir_features

class InternalNet:

    def __init__(self, behaviors):
        self.behaviors = behaviors

    def step(self, cell, node_input):

        node_state = cell.node_state

        # external input
        for k, v in node_input.items():
            node_state[k] = 0.9 * node_state.get(k, 0.0) + v / (1 + v)
        # =========================
        # 🔥 非线性 gating（核心升级）
        # =========================

        IFN_eff = node_input.get("IFN_effective", 0.0)
        threshold = cell.feature_params.get("IFN_response_threshold", 1.0)

        if IFN_eff > threshold:
            gated_IFN = (IFN_eff - threshold) ** 1.5
        else:
            gated_IFN = 0.0

        # 👉 写回 node_state（影响后续 graph）
        node_state["IFN_signal_effective"] = gated_IFN
        # 1️⃣ node graph
        node_state = run_node_graph(node_state)

        # 2️⃣ HIR
        features = build_hir_features(
            node_state,
            cell.feature_params
        )
        print("DEBUG feature_params:", cell.feature_params)
        hir_output = compute_HIR(features)

        # 3️⃣ behavior
        behavior_outputs = evaluate_behaviors(
            node_state,
            hir_output,
            self.behaviors
        )

        # 4️⃣ state update
        node_state = apply_state_update(
            node_state,
            behavior_outputs,
            {b["behavior_id"]: b for b in self.behaviors}
        )

        cell.node_state = node_state

        return {
            "behaviors": behavior_outputs,
            "hir": hir_output,
            "fate": hir_output["fate"],
            "features": features
        }
