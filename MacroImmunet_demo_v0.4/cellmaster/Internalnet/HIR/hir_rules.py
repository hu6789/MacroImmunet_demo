# Internalnet/HIR/hir_rules.py

from .hir_params import HIR_PARAMS


# =========================
# utils
# =========================

def clamp(x, low=0.0, high=1.5):
    return max(low, min(high, x))


# =========================
# Fate Evaluation（🔥可调结构）
# =========================

FATE_WEIGHTS = {
    "dying": {
        "damage": 0.7,
        "stress": 0.6,
        "energy": -0.4
    },
    "stressed": {
        "stress": 0.8,
        "damage": 0.3,
        "energy": -0.2
    },
    "normal": {
        "energy": 0.6,
        "stress": -0.4,
        "damage": -0.3
    }
}


def compute_fate_scores(f):

    scores = {}

    for fate, weights in FATE_WEIGHTS.items():
        val = 0.0
        for k, w in weights.items():
            val += w * f.get(k, 0.0)
        scores[fate] = clamp(val)

    return scores


def decide_fate(scores, features):

    if scores["dying"] > 0.2 or features["damage"] > 0.05:
        return "dying"

    if scores["stressed"] > 0.4:
        return "stressed"

    return "normal"


# =========================
# Group Modifiers
# =========================

def compute_group_modifier(name, f):

    # 🔥 fallback（关键）
    if name not in HIR_PARAMS:
        return 1.0

    p = HIR_PARAMS[name]

    if name == "cytokine_secretion":
        val = (
            p["viral_weight"] * f["viral_load"]
            + p["baseline"]
            - p["stress_weight"] * f["stress"]
            - p["damage_weight"] * f["damage"]
        )

    elif name == "metabolism":
        val = (
            p["energy_weight"] * f["energy"]
            - p["stress_weight"] * f["stress"]
            - p["viral_weight"] * f["viral_load"]
        )

    elif name == "stress_response":
        val = (
            p["stress_weight"] * f["stress"]
            + p["damage_weight"] * f["damage"]
            - p["energy_penalty"] * (1 - f["energy"])
        )

    elif name == "effector":
        val = (
            p["energy_weight"] * f["energy"]
            - p["stress_weight"] * f["stress"]
            - p["damage_weight"] * f["damage"]
        )

    elif name == "fate_execution":
        return p["baseline"]

    else:
        return 1.0

    return max(p.get("min_output", 0.0), clamp(val))


# =========================
# Blocks（硬约束）
# =========================

def compute_blocks(features, fate):

    blocks = {}

    if fate == "dying":
        blocks["division"] = True
        blocks["metabolism"] = True
        blocks["effector"] = True

    if features["stress"] > 0.9:
        blocks["cytokine_secretion"] = True

    return blocks


# =========================
# 主入口
# =========================

def run_hir(features):

    scores = compute_fate_scores(features)
    fate = decide_fate(scores, features)

    group_modifiers = {
        name: compute_group_modifier(name, features)
        for name in HIR_PARAMS.keys()
    }

    blocks = compute_blocks(features, fate)

    return {
        "fate": fate,
        "scores": scores,
        "group_modifiers": group_modifiers,
        "blocks": blocks
    }
