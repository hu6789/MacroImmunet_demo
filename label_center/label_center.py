# NOTE:
# Commit/apply path intentionally explicit.
# Possible refactor: unify transaction state switch after Phase1.

class LabelCenter:
    def __init__(self):
        self.intent_queue = []      # [{intents, source, tick}]
        self.field = {}             # coord -> {label: amount}
        self.events = []
        self._grid_summary_cache = None

    def enqueue_intents(self, intents, source=None, tick=None):
        if not intents:
            return
        self.intent_queue.append({
            "intents": intents,
            "source": source,
            "tick": tick,
        })
        print("ENQUEUE into LabelCenter id:", id(self))


    def apply_tick(self, tick=None):
        print("APPLY INTENTS:", self.intent_queue)

        for batch in self.intent_queue:
            for intent in batch["intents"]:
                self._apply_intent(intent)

        self.intent_queue.clear()
        self._grid_summary_cache = None

    def _apply_intent(self, intent):
        name = intent.get("name")
        payload = intent.get("payload", {})

        if name == "emit_label":
            coord = tuple(payload["coord"])
            label = payload["label"]
            amount = float(payload.get("amount", 1.0))

            self.field.setdefault(coord, {})
            self.field[coord][label] = (
                self.field[coord].get(label, 0.0) + amount
            )

    def get_grid_summary(self):
        if self._grid_summary_cache is not None:
            return self._grid_summary_cache

        summary = {}
        for coord, labels in self.field.items():
            summary[coord] = {"labels": dict(labels)}

        self._grid_summary_cache = summary
        return summary

