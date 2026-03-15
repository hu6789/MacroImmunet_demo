# asi/asi.py

from .input_normalizer import normalize_specificity_input
from .specificity_matcher import match_specificity
from .gating_projector import project_gating
from .asi_adapter import ASIAdapter
from .output import build_asi_output


class AdaptiveSpecificityInterpreter:
    def patch_decision_input(self, *, context, decision_input) -> dict:
        """
        返回一个 patch dict，用于 merge 进 decision_input
        """
    """
    ASI glue layer
    """

    def __init__(self, adapter: ASIAdapter):
        self.adapter = adapter

    def run(
        self,
        *,
        raw_input,
        source,
        receptors,
        cell_context,
        decision_input,
    ):
        normalized = normalize_specificity_input(
            raw_input, 
            source=source
        )

        cell_profile = {
            "recognition": {
                r["receptor_id"]: ["E1"]   # demo默认能识别
                for r in receptors
            }
        }

        match_result = match_specificity(
            normalized,
            cell_profile,
        )

        gating = project_gating(
            match_result,
            decision_input
        )

        patch = self.adapter.apply(
            cell_context=cell_context,
            gating_result=gating,
            decision_input=decision_input,
        )

        return build_asi_output(
            gating_result=gating,
            adapter_patch=patch,
        )

