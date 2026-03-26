# IntentBuilder/intent_builder.py

from .behavior_interpreter import interpret_behavior
from .fate_filter import apply_fate_filter
from .intent_binding import bind_intent


class IntentBuilder:

    def __init__(self, behaviors):
        self.behavior_defs = {
            b["behavior_id"]: b for b in behaviors
        }

    def build(self, cell, result):

        intents = []

        fate = result["fate"]

        # =========================
        # ① fate → 硬优先（当前版本）
        # =========================
        if fate == "dying":
            return [{
                "type": "die",
                "cell_id": cell.cell_id
            }]

        # =========================
        # ② behavior → spec
        # =========================
        specs = []

        for b in result["behaviors"]:

            bdef = self.behavior_defs[b["behavior_id"]]

            spec = interpret_behavior(b, bdef)

            if spec:
                specs.append(spec)

        # =========================
        # ③ fate filter（未来扩展点）
        # =========================
        specs = apply_fate_filter(specs, fate)

        # =========================
        # ④ binding → intent
        # =========================
        for s in specs:

            intent = bind_intent(s, cell, self.behavior_defs)

            if intent:
                intents.append(intent)

        # =========================
        # debug（可选）
        # =========================
        # print("INTENT TRACE:", intents)

        return intents
