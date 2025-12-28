# cell_master/masters/native_t_master.py
"""
NativeTMaster - Naive T cell demo master focused on activation & differentiation.

Behavior summary:
 - Expects cell_meta to represent a naive T; detects IL12 / pMHC / DC cues.
 - Differentiates -> emits:
     * {"name":"change_type","payload":{"new_type":"TH1"/"CTL"}}
     * {"name":"mark","payload":{"flag":"differentiated_to","value":"TH1"/"CTL"}}
     * {"name":"handover_label","payload":{"label":"ANTIGEN_HANDOVER","from_type":"NAIVE_T","to_type":"DC"}}
   and mutates cell_meta["type"] and cell_meta["activated"].
 - After differentiation TH1 does a first-round secretion (IFNG/IL2).
 - CTL gets an active mark.
 - If no decisive cue -> random_move or light activation mark.
"""
from typing import Dict, Any, List, Optional, Tuple
import random

_ACTION_RANDOM_MOVE = "random_move"
_ACTION_CHANGE_TYPE = "change_type"
_ACTION_SECRETE = "secrete"
_ACTION_MARK = "mark"
_ACTION_HANDOVER = "handover_label"

class NativeTMaster:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = dict(config or {})
        # thresholds / probabilities
        self.il12_threshold = float(cfg.get("il12_threshold", 1.0))
        self.p_differentiate_on_pmhc = float(cfg.get("p_differentiate_on_pmhc", 0.9))
        self.p_th1_given_il12 = float(cfg.get("p_th1_given_il12", 0.85))
        # effector amounts
        self.ifng_amount = float(cfg.get("ifng_amount", 1.0))
        self.il2_amount = float(cfg.get("il2_amount", 1.0))
        # misc
        self.debug = bool(cfg.get("debug", False))

    def step(self, coord: Optional[Tuple[float, float]], summary: Dict[str, Any],
             cell_meta: Dict[str, Any], rng=None) -> List[Dict[str, Any]]:
        rng = rng or random.Random()
        summary = summary or {}
        cell_meta = cell_meta or {}
        actions: List[Dict[str, Any]] = []

        # canonicalize cell type
        ctype = (str(cell_meta.get("type") or cell_meta.get("cell_type") or "NAIVE_T")).upper()
        if self.debug:
            print("[NativeTMaster] tick type=", ctype, "meta=", dict(cell_meta))

        # operate only for naive T-like cells (fallback: treat empty as NAIVE_T)
        if ctype not in ("NAIVE_T", "NAIVE", ""):
            # If already TH1/CTL we keep simple: TH1 secretes, CTL marks active
            if ctype == "TH1":
                return self._th1_behavior(summary, cell_meta, rng)
            if ctype == "CTL":
                return self._ctl_behavior(summary, cell_meta, rng)
            # unknown types - random move
            return [{"name": _ACTION_RANDOM_MOVE, "payload": {"coord": coord}}]

        # signals
        il12_val = self._fetch_field_value(summary, "IL12") or 0.0
        sees_pmhc = bool(summary.get("pMHC_present") or summary.get("pMHC_hotspot"))
        sees_dc_presenting = bool(summary.get("DC_presenting"))

        # IL-12 bias: if IL12 above threshold, bias to Th1
        if il12_val >= self.il12_threshold:
            if self.debug:
                print("[NativeTMaster] IL12 present:", il12_val)
            if rng.random() < self.p_th1_given_il12:
                return self._differentiate_th1_and_handover(cell_meta)
            # otherwise continue to pMHC decision below

        # pMHC or DC presenting are strong cues for differentiation
        if sees_pmhc or sees_dc_presenting:
            if self.debug:
                print("[NativeTMaster] pMHC/DC cues present")
            if rng.random() < self.p_differentiate_on_pmhc:
                # bias decision by IL12 presence
                prob_th1 = self.p_th1_given_il12 if il12_val >= self.il12_threshold else (self.p_th1_given_il12 * 0.4)
                if rng.random() < prob_th1:
                    return self._differentiate_th1_and_handover(cell_meta)
                else:
                    return self._differentiate_ctl_and_handover(cell_meta)

        # small chance to become lightly activated without differentiating
        if rng.random() < 0.02:
            cell_meta["activated"] = True
            return [{"name": _ACTION_MARK, "payload": {"flag": "naive_activated", "value": True}}]
        # ---- CTL kill infected target (Step2.2 minimal) ----
        if cell_meta.get("type") == "CTL":
            targets = summary.get("targets") or []
            if targets:
                return [{
                    "name": "external_apoptosis",
                    "target": targets[0],
                    "source": coord,
                    "mode": "CTL_contact_kill",
                }]

        # ---- fallback: random move ----
        return [{"name": _ACTION_RANDOM_MOVE, "payload": {"coord": coord}}]

    # ---------------- helpers ----------------

    def _differentiate_th1_and_handover(self, cell_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        # mutate metadata
        cell_meta["type"] = "TH1"
        cell_meta["activated"] = True
        # actions: change_type, mark, secrete (initial), handover_label
        acts: List[Dict[str, Any]] = []
        acts.append({"name": _ACTION_CHANGE_TYPE, "payload": {"new_type": "TH1"}})
        acts.append({"name": _ACTION_MARK, "payload": {"flag": "differentiated_to", "value": "TH1"}})
        # initial cytokine burst to signal differentiation
        acts.append({"name": _ACTION_SECRETE, "payload": {"label": "IFNG", "amount": float(self.ifng_amount)}})
        acts.append({"name": _ACTION_SECRETE, "payload": {"label": "IL2", "amount": float(self.il2_amount)}})
        # handover label: indicate antigen handover opportunity (DCs can pick this up)
        acts.append({"name": _ACTION_HANDOVER, "payload": {"label": "ANTIGEN_HANDOVER", "from_type": "NAIVE_T", "to_type": "DC"}})
        if self.debug:
            print("[NativeTMaster] differentiated -> TH1 and emitted handover label")
        return acts

    def _differentiate_ctl_and_handover(self, cell_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        cell_meta["type"] = "CTL"
        cell_meta["activated"] = True
        acts: List[Dict[str, Any]] = []
        acts.append({"name": _ACTION_CHANGE_TYPE, "payload": {"new_type": "CTL"}})
        acts.append({"name": _ACTION_MARK, "payload": {"flag": "differentiated_to", "value": "CTL"}})
        # emit handover label too (some workflows want CTL to also mark antigen handover)
        acts.append({"name": _ACTION_HANDOVER, "payload": {"label": "ANTIGEN_HANDOVER", "from_type": "NAIVE_T", "to_type": "DC"}})
        if self.debug:
            print("[NativeTMaster] differentiated -> CTL and emitted handover label")
        return acts

    def _th1_behavior(self, summary: Dict[str, Any], cell_meta: Dict[str, Any], rng) -> List[Dict[str, Any]]:
        il12_val = self._fetch_field_value(summary, "IL12") or 0.0
        sees_antigen = bool(summary.get("agents") or summary.get("cells"))
        if cell_meta.get("activated") or sees_antigen or il12_val > 0:
            amount_ifng = self.ifng_amount * (1.0 + min(float(il12_val), 4.0) * 0.2)
            amount_il2 = self.il2_amount * (1.0 + (1.0 if cell_meta.get("activated") else 0.0))
            return [
                {"name": _ACTION_SECRETE, "payload": {"label": "IFNG", "amount": float(amount_ifng)}},
                {"name": _ACTION_SECRETE, "payload": {"label": "IL2", "amount": float(amount_il2)}},
                {"name": _ACTION_MARK, "payload": {"flag": "TH1_ACTIVE", "value": True}},
            ]
        return [{"name": _ACTION_RANDOM_MOVE, "payload": {"coord": None}}]

    def _ctl_behavior(
        self,
        summary: Dict[str, Any],
        cell_meta: Dict[str, Any],
        rng
    ) -> List[Dict[str, Any]]:

        # ---- Step2.2 minimal: CTL contact kill ----
        targets = summary.get("targets") or []
        if targets:
            return [{
                "name": "external_apoptosis",
                "target": targets[0],
                "source": None,
                "mode": "CTL_contact_kill",
            }]

        # ---- fallback: random move ----
        return [{
            "name": _ACTION_RANDOM_MOVE,
            "payload": {"coord": None}
        }]


    def _fetch_field_value(self, summary: Dict[str, Any], field_name: str) -> Optional[float]:
        v = summary.get(field_name)
        if v is None:
            return None
        try:
            if isinstance(v, dict) and "value" in v:
                return float(v.get("value"))
            return float(v)
        except Exception:
            return None

# export
__all__ = ["NativeTMaster"]

