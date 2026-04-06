def apply_input_to_state(node_state, node_input, node_defs):
    new_state = dict(node_state)

    for k, v in node_input.items():
        node_def = node_defs.get(k, {})

        mode = node_def.get("input_mode", "overwrite")

        if mode == "overwrite":
            new_state[k] = v

        elif mode == "add":
            new_state[k] = new_state.get(k, 0.0) + v

        elif mode == "max":
            new_state[k] = max(new_state.get(k, 0.0), v)

    return new_state
def apply_state_update(
    node_state,
    behavior_outputs,
    node_defs,
    hir_output=None
):

    new_state = dict(node_state)

    # =========================
    # 1️⃣ Behavior → state
    # =========================
    for b in behavior_outputs:

        output = b.get("output", {})
        if not output:
            continue

        if output.get("type") != "internal_state":
            continue

        target = output.get("target")
        merge_mode = output.get("merge_mode", "add")

        # 👉 强度来源
        if output.get("intensity_source") == "drive":
            intensity = b.get("drive", 0.0)
        else:
            intensity = output.get("value", 0.0)

        # 👉 activation scaling
        intensity *= b.get("activation", 1.0)

        # 👉 HIR modulation
        if hir_output:
            if hir_output.get("fate", None) == "dying":
                intensity *= 0.5

        # =========================
        # 🔥 state_effects
        # =========================
        state_effects = output.get("state_effects", {})
        for k, v in state_effects.items():
            old = new_state.get(k, 0.0)
            new_state[k] = old + v * b.get("activation", 1.0)

    # =========================
    # 🔥 2️⃣ NEW: dynamics layer（核心新增）
    # =========================
    updated_state = dict(new_state)

    for node_id, node_def in node_defs.items():

        val = new_state.get(node_id, 0.0)
        prev = node_state.get(node_id, 0.0)

        dynamics = node_def.get("dynamics", "instant")

        # -------------------------
        # 🧠 ① Instant（默认）
        # -------------------------
        if dynamics == "instant":
            updated_val = val

        # -------------------------
        # 🧠 ② Integrator（累积型🔥）
        # -------------------------
        elif dynamics == "integrator":
            decay = node_def.get("decay_rate", 0.9)
            gain = node_def.get("gain", 1.0)

            # 👉 当前写法：行为已经写进 val，所以我们提取“新增量”
            delta = val - prev

            updated_val = prev * decay + delta * gain

        # -------------------------
        # 🧠 ③ Leaky（带baseline回归）
        # -------------------------
        elif dynamics == "leaky":
            decay = node_def.get("decay_rate", 0.9)
            baseline = node_def.get("baseline", 0.0)

            updated_val = prev * decay + (1 - decay) * baseline + (val - prev)

        # -------------------------
        # 🧠 ④ Switch（阈值）
        # -------------------------
        elif dynamics == "switch":
            threshold = node_def.get("threshold", 0.5)

            updated_val = 1.0 if val > threshold else 0.0

        else:
            updated_val = val

        updated_state[node_id] = updated_val

    new_state = updated_state

    # =========================
    # 3️⃣ Decay / baseline（保留你原有机制）
    # =========================
    for node_id, node_def in node_defs.items():

        decay_cfg = node_def.get("decay", {})

        mode = decay_cfg.get("mode", "none")
        tau = decay_cfg.get("tau", None)
        baseline = node_def.get("baseline", 0.0)

        val = new_state.get(node_id, 0.0)

        if mode == "none" or tau is None:
            continue

        if mode == "exponential":
            val = val + (baseline - val) / tau
        elif mode == "linear":
            if val > baseline:
                val -= (val - baseline) / tau
            else:
                val += (baseline - val) / tau

        new_state[node_id] = val

    # =========================
    # 4️⃣ clamp（安全）
    # =========================
    for k in new_state:
        new_state[k] = max(0.0, min(1.0, new_state[k]))

    return new_state
