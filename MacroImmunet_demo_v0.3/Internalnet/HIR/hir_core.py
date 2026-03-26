# HIR/hir_core.py

from .hir_context import build_features
from .hir_rules import run_hir


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


def compute_HIR(node_state):
    features = build_features(node_state)
    return run_hir(features)
