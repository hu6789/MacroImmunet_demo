# Internalnet/HIR/hir_context.py

def build_features(node_state):
    """
    将 node_state 映射为 HIR features
    """

    def safe_get(key, default=0.0):
        return node_state.get(key, default)

    features = {}

    # =========================
    # 🧬 核心生理变量
    # =========================

    features["energy"] = safe_get("ATP", 0.5)

    features["stress"] = safe_get("stress", 0.0)

    features["damage"] = safe_get("damage", 0.0)

    features["viral_load"] = safe_get("viral_RNA", 0.0)

    # =========================
    # 🧪 可扩展（未来用）
    # =========================

    features["inflammation"] = safe_get("inflammation_signal", 0.0)

    features["apoptosis_drive"] = safe_get("apoptosis_drive", 0.0)

    return features
