import json
import os

from .field_registry import FIELD_REGISTRY


class LabelCenter:

    def __init__(self, init_field, space=None):

        self.fields = init_field.copy()
        self.queue = []
        self.space = space   # ✅ 现在合法了

        config_path = os.path.join(
            os.path.dirname(__file__), "field_config.json"
        )

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    # =========================
    # 🔹 读接口
    # =========================

    def get_field(self, key):
        return self.fields.get(key, 0.0)

    def get_all(self):
        return self.fields.copy()

    # =========================
    # 🔹 写接口（延迟）
    # =========================

    def enqueue(self, intents):
        self.queue.extend(intents)

    # =========================
    # 🔹 核心 apply
    # =========================

    def apply(self):

        # 1️⃣ intents
        for intent in self.queue:

            if intent["type"] == "add_field":

                target = intent["target"]
                value = intent["value"]
                cell_id = intent.get("cell_id")

                if target not in self.fields:
                    self.fields[target] = 0.0

                self.fields[target] += value
                if self.space:
                    pos = self.space.get_cell_pos(intent["cell_id"])
                    self.space.add_local_field(pos, target, value)

                # ✅ NEW：同步到空间
                if self.space and cell_id:
                    pos = self.space.get_cell_pos(cell_id)
                    self.space.add_local_field(pos, target, value)

                target = intent["target"]

                if target not in self.fields:
                    self.fields[target] = 0.0

                self.fields[target] += intent["value"]

            elif intent["type"] == "die":
                self.fields["damage"] += 1.0

        # 2️⃣ decay + saturation
        for k in list(self.fields.keys()):

            meta = FIELD_REGISTRY.get(k, {})

            # 🔹 decay
            if meta.get("type") == "substance":
                decay = meta.get("decay", 0.0)
                self.fields[k] *= (1 - decay)

            # 🔹 saturation
            max_v = meta.get("max", None)
            if max_v is not None:
                self.fields[k] = min(self.fields[k], max_v)

        # 3️⃣ clear
        self.queue.clear()

    def get_meta(self, field_name):
        return FIELD_REGISTRY.get(field_name, {})
