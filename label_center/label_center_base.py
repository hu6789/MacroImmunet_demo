# Ownership arbitration is rule-based and distributed:
# - owned labels skip decay
# - claimed labels ignore emit
# - claim/reclaim gated by cooldown
# Explicit conflict resolver may be introduced in Phase 2 if needed.
"""
LabelCenterBase
================
Phase1 stable implementation.

Semantics guaranteed:
- Tick-atomic writes
- Ownership exclusivity
- Hysteresis / cooldown
- Deterministic conflict resolution

⚠️ Do not change semantics without bumping major version.
"""

from collections import defaultdict
import math

class LabelCenterBase:
    """
    Step5.2
    Label Center with time decay
    """

    def __init__(
        self,
        decay_rate=0.9,
        claim_cooldown=0,
        prune_threshold=0.0,
    ):
        self.decay_rate = decay_rate
        self.claim_cooldown = claim_cooldown
        self.prune_threshold = prune_threshold

        self.current_tick = 0

    # coord -> label -> entry
        self.label_field = defaultdict(lambda: {})
        self.field = self.label_field

    # ---------- Step5.1 ----------
    def consume_intents(self, intents):
        for intent in intents:
            self._consume_intent(intent)

    def _consume_intent(self, intent):
        if intent.get("name") != "emit_label":
            return

        payload = intent.get("payload", {})
        coord = payload.get("coord")
        label = payload.get("label")
        amount = payload.get("amount", 0.0)

        if coord is None or label is None:
            return

        entry = self.label_field[coord].get(label)

    # ---------- Step5.4: ownership protection ----------
        if entry is not None and entry.get("owned_by") is not None:
        # 被 per-cell 认领，library emit_label 无权修改
            return
    # --------------------------------------------------

        if entry is None:
            self.label_field[coord][label] = {
                "value": amount,
                "last_tick": self.current_tick
            }
        else:
    # 先把旧值 decay 到当前 tick
            decayed = self._decay(entry["value"], entry["last_tick"])

    # 再累加新的 amount
            entry["value"] = decayed + amount
            entry["last_tick"] = self.current_tick


    # ---------- Step5.2 ----------
    def advance_tick(self, tick: int):
        if tick < self.current_tick:
            return
        self.current_tick = tick
        
    def tick(self, step=1):
        """
        Step5.3
        Advance internal time by `step` ticks
        """
        self.current_tick += step


    def _decay(self, value, last_tick):
        dt = self.current_tick - last_tick
        if dt <= 0:
            return value
        if self.decay_rate <= 0.0:
            return value
        return value * (self.decay_rate ** dt)

    def get_label(self, coord, label):
        entry = self.label_field.get(coord, {}).get(label)
        if entry is None:
            return 0.0

        # owned labels: no decay, always visible
        if entry.get("owned_by") is not None:
            return entry.get("value", 0.0)

        value = self._decay(entry["value"], entry["last_tick"])

       # 🔑 Step5.8: perception threshold
        if value < self.prune_threshold:
            return 0.0

        return value


    def release_label(self, coord, label_name, by):
        entry = self.label_field.get(coord, {}).get(label_name)

        if entry is None:
            raise KeyError("Label not found")

        if entry.get("owned_by") != by:
            raise ValueError(
                f"Label {label_name} at {coord} not owned by {by}"
            )

        entry["owned_by"] = None
        entry["cooldown_until"] = self.current_tick + self.claim_cooldown


    def create_label(self, coord, mass, label_type):
        label_id = f"label_{len(self.labels)}"

        self.labels[label_id] = {
            "coord": coord,
            "value": mass,
            "label_type": label_type,
            "owned_by": None,
            "last_tick": self.current_tick
        }

        return label_id
    def claim_label(self, coord, label_name, by):
        entry = self.label_field.get(coord, {}).get(label_name)

        if entry is None:
            raise KeyError(f"Label {label_name} at {coord} not found")

    # 已被占用
        if entry.get("owned_by") is not None:
            return False

    # cooldown 中
        cooldown_until = entry.get("cooldown_until")
        if cooldown_until is not None and self.current_tick < cooldown_until:
            return False

        entry["owned_by"] = by
        return True
    def prune(self):
        for coord in list(self.label_field.keys()):
            labels = self.label_field[coord]
            for label in list(labels.keys()):
                entry = labels[label]

                if entry.get("owned_by") is not None:
                    continue

                value = self._decay(entry["value"], entry["last_tick"])

                if value < self.prune_threshold:
                    del labels[label]

            if not labels:
                del self.label_field[coord]

    def prune(self):
        """
        Step5.8
        Remove decayed, unowned field labels
        """
        for coord in list(self.label_field.keys()):
            labels = self.label_field[coord]

            for label in list(labels.keys()):
                entry = labels[label]

            # owned labels are protected
                if entry.get("owned_by") is not None:
                    continue

            # 🔑 先把 decay 结算到 entry 上
                decayed_value = self._decay(
                    entry["value"], entry["last_tick"]
                )

                entry["value"] = decayed_value
                entry["last_tick"] = self.current_tick

            # 🔑 再用“当前可感知值”判断
                if decayed_value < self.prune_threshold:
                    del labels[label]

            if not labels:
                del self.label_field[coord]

class LabelRegistry:
    """
    Object-level labels (super-particles)
    """
    def __init__(self):
        self.labels = {}

    def register(self, label): ...
    def claim(self, label_id, by): ...
    def release(self, label_id, by): ...
    def tick(self, dt): ...

