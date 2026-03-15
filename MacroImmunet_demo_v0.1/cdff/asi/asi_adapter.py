# asi/asi_adapter.py

from typing import Dict, List, Any, Optional


class ASIAdapter:
    """
    Adaptive Specificity Interpreter Adapter

    职责：
    - 将 ASI 的 gating / bias 结果整理为 decision-time patch
    - 不裁决、不写世界、不生成 intent
    """

    def __init__(
        self,
        *,
        max_activation_bias: float = 1.0,
    ):
        self.max_activation_bias = max_activation_bias

    def apply(
        self,
        *,
        cell_context: Dict[str, Any],
        gating_result: Optional[Dict[str, Any]],
        decision_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        返回一个 decision-time patch（不直接修改 decision_input）

        Parameters
        ----------
        cell_context : dict
            细胞上下文（cell_type / genotype / state 等）
            当前仅保留接口，不主动使用（防止偷裁决）

        gating_result : dict | None
            GatingProjector 的输出，例如：
            {
                "activation_bias": float,
                "matched_epitopes": [...],
                "matched_receptors": [...]
            }

        decision_input : dict
            原始决策输入（只读）

        Returns
        -------
        patch : dict
            {
                "activation_bias": float,
                "tags": [...]
            }
        """

        patch: Dict[str, Any] = {}

        if not gating_result:
            return patch

        bias = gating_result.get("activation_bias", 0.0)
        if bias <= 0.0:
            return patch

        # clamp，防止外部 epitope 注入过载
        bias = min(bias, self.max_activation_bias)

        patch["activation_bias"] = bias

        # tags 仅用于 debug / trace，不参与裁决
        tags: List[str] = []

        for ep in gating_result.get("matched_epitopes", []):
            ep_id = ep.get("epitope_id")
            if ep_id:
                tags.append(f"epitope:{ep_id}")

        for r in gating_result.get("matched_receptors", []):
            r_id = r.get("receptor_id")
            if r_id:
                tags.append(f"receptor:{r_id}")

        if tags:
            patch["tags"] = tags

        return patch

