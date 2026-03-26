# HIR/hir_rules.py
from .hir_params import HIR_PARAMS
def clamp(x, low=0.0, high=1.5):
    return max(low, min(high, x))


# =========================
# 🧬 Fate Evaluation（连续评分）
# =========================

def compute_fate_scores(f):
    """
    连续计算多个 fate 倾向（0~1+）
    """

    scores = {}

    # ☠️ dying（整合 apoptosis + necrosis）
    scores["dying"] = clamp(
        0.7 * f["damage"]
        + 0.6 * f["stress"]
        - 0.4 * f["energy"]
    )

    # 😵 stressed
    scores["stressed"] = clamp(
        0.8 * f["stress"]
        + 0.3 * f["damage"]
        - 0.2 * f["energy"]
    )

    # 😊 normal（反向）
    scores["normal"] = clamp(
        0.6 * f["energy"]
        - 0.4 * f["stress"]
        - 0.3 * f["damage"]
    )

    return scores


def decide_fate(scores):
    """
    从 score → fate（带阈值 + 优先级）
    """

    # 优先级：dying > stressed > normal

    if scores["dying"] > 0.8:
        return "dying"

    if scores["stressed"] > 0.6:
        return "stressed"

    return "normal"


# =========================
# ⚙️ Group Modifiers（连续调制）
# =========================

GROUP_MODIFIERS = {
    k: (lambda name: lambda f: compute_group_modifier(name, f))(k)
    for k in HIR_PARAMS.keys()
}

def compute_group_modifier(name, f):
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

    elif name == "fate_execution":
        return p["baseline"]

    else:
        return 1.0

    return max(p.get("min_output", 0.0), clamp(val))

# =========================
# 🚫 Block Rules（硬限制）
# =========================

def compute_blocks(features, fate):

    blocks = {}

    # ☠️ dying
    if fate == "dying":
        blocks["division"] = True
        blocks["metabolism"] = True
        # ❗ 不 block cytokine（让 modifier 控制）

    # ⚠️ 极端 stress 才硬禁
    if features["stress"] > 0.9:
        blocks["cytokine_secretion"] = True

    return blocks


# =========================
# 🎯 主接口（给 run_loop 用）
# =========================

def run_hir(features):
    """
    统一入口（你 run_loop 直接调这个）
    """

    scores = compute_fate_scores(features)
    fate = decide_fate(scores)

    group_modifiers = {
        k: fn(features) for k, fn in GROUP_MODIFIERS.items()
    }

    blocks = compute_blocks(features, fate)

    return {
        "fate": fate,
        "scores": scores,   # ⭐ 新增（调试神器）
        "group_modifiers": group_modifiers,
        "blocks": blocks
    }
