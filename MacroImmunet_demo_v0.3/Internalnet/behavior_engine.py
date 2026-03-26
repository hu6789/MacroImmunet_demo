def evaluate_behaviors(node_state, hir_output, behaviors):

    outputs = []

    for behavior in behaviors:

        # 1️⃣ gate（可以保留硬门）
        gate_ok = True
        for g in behavior.get("gate", []):
            if node_state.get(g["node"], 0.0) < g["threshold"]:
                gate_ok = False
                break

        if not gate_ok:
            continue

        # 2️⃣ drive
        drive = 0.0
        for item in behavior["drive"]["inputs"]:
            drive += node_state.get(item["node"], 0.0) * item["weight"]

        # 3️⃣ HIR 调制（连续）
        hir_cfg = behavior.get("hir_interaction", {})
        group = behavior.get("group", None)

        if hir_cfg.get("use_modifier", False) and group:

            # block → 弱化，而不是归零
            if hir_cfg.get("blockable", False):
                if hir_output["blocks"].get(group, False):
                    drive *= 0.05

            # global scale
            if hir_cfg.get("use_global_scale", False):
                scale = hir_output["group_modifiers"].get(group, 1.0)
                drive *= scale

        # 4️⃣ activation（连续）
        act_cfg = behavior["activation"]

        if act_cfg["mode"] == "deterministic":
            act = 1.0 if drive >= act_cfg["threshold"] else 0.0

        elif act_cfg["mode"] == "probabilistic":
            import math
            x = drive - act_cfg["threshold"]
            slope = act_cfg.get("slope", 4.0)
            act = 1 / (1 + math.exp(-slope * x))

        else:
            act = 0.0

        # 5️⃣ 输出（软阈值）
        output_threshold = behavior.get("output_threshold", 0.1)

        if act >= output_threshold:
            outputs.append({
                "behavior_id": behavior["behavior_id"],
                "activation": act,
                "drive": drive,
                "group": group
            })

    return outputs
