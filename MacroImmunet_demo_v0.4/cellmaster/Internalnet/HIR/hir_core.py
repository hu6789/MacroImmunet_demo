# Internalnet/HIR/hir_core.py

from .hir_rules import run_hir
from .hir_features import build_hir_features


def compute_HIR(node_state, cell):
    """
    🔥 v0.4 标准入口（唯一合法入口）

    输入：
        node_state: 当前节点状态
        cell: cell instance（用于 feature_params）

    输出：
        {
            fate,
            scores,
            group_modifiers,
            blocks
        }
    """

    features = build_hir_features(
        node_state,
        cell.feature_params
    )

    return run_hir(features)
