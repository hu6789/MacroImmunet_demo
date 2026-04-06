# Internalnet/behavior_engine.py

import math

def build_behavior_inputs_from_graph(graph):
    inputs_map = {}

    for edge in graph.get("edges", []):

        edge_type = edge.get("type", "")

        # ✅ 放宽匹配（防止格式不统一）
        if "node" in edge_type and "behavior" in edge_type:
            pass
        elif edge_type == "":
            # ⚠️ 没写 type，也当 node->behavior
            pass
        else:
            continue

        src = edge.get("source")
        tgt = edge.get("target")

        if not src or not tgt:
            continue

        inputs_map.setdefault(tgt, []).append({
            "node": src,
            "weight": edge.get("weight", 1.0)
        })

    return inputs_map
def evaluate_behaviors(node_state, hir_output, behaviors, cell=None, graph=None):
    if graph:
        print("[INFO] Graph provided but behavior inputs come from behavior.json")
    if graph:
        print("[DEBUG] graph.behaviors RAW:", graph.get("behaviors"))
    outputs = []
    fate = hir_output.get("fate", "normal")

    # ✅ 从 graph 取允许的 behaviors
    allowed_behaviors = set()
    if graph:
        raw_behaviors = graph.get("behaviors", [])
 
        # -------------------------
        # 🧠 三种结构兼容
        # -------------------------

        if isinstance(raw_behaviors, dict):
            # ✅ 现在你的情况（dict）
            allowed_behaviors = set(raw_behaviors.keys())

        elif raw_behaviors and isinstance(raw_behaviors[0], str):
            # ✅ list[str]
            allowed_behaviors = set(raw_behaviors)

        else:
            # ✅ list[dict]
            allowed_behaviors = set(
                b["behavior_id"] for b in raw_behaviors
            )

        print("Allowed behaviors:", allowed_behaviors)
        
    behavior_inputs_map = {}
    if graph:
        behavior_inputs_map = build_behavior_inputs_from_graph(graph)
    print(f"[DEBUG] behavior_inputs_map:", behavior_inputs_map)

    for behavior in behaviors:

        behavior_name = behavior["behavior_id"]

        # -------------------------
        # allowed filter
        # -------------------------
        if graph:
            if behavior_name not in allowed_behaviors:
                continue

        # -------------------------
        # drive config（必须在外层）
        # -------------------------
        drive_cfg = behavior.get("drive")
        if not drive_cfg:
            print(f"[WARN] skip behavior {behavior_name}: no drive config")
            continue

        drive_type = drive_cfg.get("type", "weighted_sum")

        # -------------------------
        # inputs
        # -------------------------
        inputs = drive_cfg.get("inputs")

        # fallback（如果没写 inputs 才用 graph）
        if not inputs and graph:
            inputs = behavior_inputs_map.get(behavior_name, [])
 
        print(f"[DEBUG] {behavior_name} inputs:", inputs)

        group = behavior.get("functional_group", "default")

        # =========================
        # 1️⃣ Fate gating
        # =========================
        if fate == "dying" and group != "fate_execution":
            continue

        # =========================
        # 2️⃣ Gate
        # =========================
        gates = behavior.get("gate", [])
        gate_logic = behavior.get("gate_logic", "all")

        if gates:
            results = []
            for g in gates:
                val = node_state.get(g["node"], 0.0)
                results.append(val >= g["threshold"])

            if gate_logic == "all":
                if not all(results):
                    continue
            elif gate_logic == "any":
                if not any(results):
                    continue

        # =========================
        # 3️⃣ Drive
        # =========================
        values = [
            node_state.get(i["node"], 0.0) * i.get("weight", 1.0)
            for i in inputs
        ]

        if not values:
            print(f"[WARN] {behavior_name} has no inputs → drive=0")
            drive = 0.0

        elif drive_type == "weighted_sum":
            drive = sum(values)

        elif drive_type == "product":
            drive = math.prod(values)

        elif drive_type == "max":
            drive = max(values)

        else:
            drive = 0.0

        # normalize
        if drive_cfg.get("normalize", False):
            drive = min(1.0, drive)

        # =========================
        # 4️⃣ HIR modulation
        # =========================
        hir_cfg = behavior.get("hir_interaction", {})

        if hir_cfg.get("blockable", False):
            if hir_output["blocks"].get(group, False):
                drive *= 0.05

        if hir_cfg.get("scalable", False):
            drive *= hir_output["group_modifiers"].get(group, 1.0)

        # =========================
        # 5️⃣ Cell params
        # =========================
        bp = {}
        if cell:
            bp = cell.behavior_params.get(behavior_name, {})
            drive *= bp.get("sensitivity", 1.0)

        # =========================
        # 6️⃣ Activation
        # =========================
        act_cfg = behavior.get("activation", {})

        threshold = act_cfg.get("threshold", 0.0)
        threshold += bp.get("threshold_shift", 0.0)

        if act_cfg.get("mode", "deterministic") == "deterministic":
            act = 1.0 if drive >= threshold else 0.0
        else:
            x = drive - threshold
            slope = act_cfg.get("slope", 4.0)
            act = 1 / (1 + math.exp(-slope * x))

        output_threshold = act_cfg.get("output_threshold", 0.1)

        if act < output_threshold:
            continue

        # =========================
        # 7️⃣ Output
        # =========================
        outputs.append({
            "behavior_id": behavior_name,
            "activation": act,
            "drive": drive,
            "functional_group": group,
            "effect_scope": behavior.get("effect_scope", "internal"),
            "output": dict(behavior.get("output", {}))
        })
    return outputs
