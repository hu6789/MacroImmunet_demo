# HIR/hir_context.py

def clamp(x, low=0.0, high=1.0):
    return max(low, min(high, x))


def build_features(cell_state):
    """
    将 cell_state 转换为 HIR 使用的标准 feature
    
    输入: cell_state (dict)
    输出: features (dict)
    """

    features = {}

    # === 基础状态 ===
    features["energy"] = clamp(cell_state.get("ATP", 0.5))
    features["stress"] = clamp(cell_state.get("stress", 0.0))
    features["damage"] = clamp(cell_state.get("damage", 0.0))

    # === 病毒相关 ===
    features["viral_load"] = clamp(cell_state.get("viral_RNA", 0.0))

    # === 可扩展（以后加）===
    # features["inflammation"] = ...
    # features["signal_strength"] = ...

    return features
