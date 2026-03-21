# HIR/hir_rules.py

def clamp(x, low=0.0, high=1.5):
    return max(low, min(high, x))


# =========================
# 🧬 Fate Rules
# =========================

FATE_RULES = [

    {
        "name": "apoptosis",
        "condition": lambda f: f["damage"] > 0.8 and f["energy"] < 0.3,
        "fate": "dying"
    },

    {
        "name": "high_stress",
        "condition": lambda f: f["stress"] > 0.7,
        "fate": "stressed"
    }

]


# =========================
# ⚙️ Group Modifiers
# =========================

GROUP_MODIFIERS = {

    # 🧪 分泌
    "cytokine_secretion": lambda f:
        clamp(
            1.2 * f["viral_load"]
            + 0.5
            - 0.7 * f["stress"]
            - 0.8 * f["damage"]
        ),

    # ⚙️ 代谢
    "metabolism": lambda f:
        clamp(
            f["energy"]
            - 0.6 * f["stress"]
            - 0.3 * f["viral_load"]
        ),

    # 🛡 应激
    "stress_response": lambda f:
        clamp(
            f["stress"]
            + 0.5 * f["damage"]
            - 0.5 * (1 - f["energy"])
        ),

    # ☠️ 命运执行（只作为标识，不直接scale）
    "fate_execution": lambda f: 1.0
}


# =========================
# 🚫 Block Rules（硬禁止）
# =========================

def compute_blocks(features, fate):

    blocks = {}

    # 如果进入 dying → 禁止非命运行为
    if fate == "dying":
        blocks["division"] = True
        blocks["metabolism"] = True

    # stress 过高 → 抑制分泌
    if features["stress"] > 0.8:
        blocks["cytokine_secretion"] = True

    return blocks
