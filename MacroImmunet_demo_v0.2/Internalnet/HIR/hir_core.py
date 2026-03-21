# HIR/hir_core.py

from .hir_context import build_features
from .hir_rules import FATE_RULES, GROUP_MODIFIERS, compute_blocks


def evaluate_fate(features):
    """
    顺序匹配 fate（可改优先级）
    """
    for rule in FATE_RULES:
        if rule["condition"](features):
            return rule["fate"]
    return "normal"


def compute_group_modifiers(features):
    """
    计算每个 group 的 scale
    """
    modifiers = {}

    for group, func in GROUP_MODIFIERS.items():
        modifiers[group] = func(features)

    return modifiers


def compute_HIR(cell_state, logger=None):
    """
    主入口
    
    输入:
        cell_state (dict)
    输出:
        HIR_output (dict)
    """

    # === 1️⃣ 构建特征 ===
    features = build_features(cell_state)

    if logger:
        logger.log("HIR_features", features)

    # === 2️⃣ fate 判定 ===
    fate = evaluate_fate(features)

    # === 3️⃣ group scale ===
    group_modifiers = compute_group_modifiers(features)

    # === 4️⃣ block ===
    blocks = compute_blocks(features, fate)

    # === 输出 ===
    HIR_output = {
        "fate": fate,
        "group_modifiers": group_modifiers,
        "blocks": blocks
    }

    if logger:
        logger.log("HIR_output", HIR_output)

    return HIR_output
