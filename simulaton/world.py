class World:
    def __init__(self, scan_master, cell_master, label_center):
        self.scan_master = scan_master
        self.cell_master = cell_master
        self.label_center = label_center
        self.tick_count = 0

    def tick(self):   # 👈 注意：4 个空格缩进
        nodes = self.scan_master.scan()

        self.cell_master.handle_nodes(
            nodes,
            region_id="default",
            tick=self.tick_count
        )

        intents = getattr(self.cell_master, "intent_queue", [])

        if not intents:
            intents = [{
                "name": "emit_label",
                "payload": {
                    "coord": (0, 0),
                    "label": "bootstrap",
                    "amount": 1.0
                }
            }]

        self.label_center.enqueue_intents(
            intents,
            source="world_bootstrap",
            tick=self.tick_count
        )

        self.label_center.apply_tick(tick=self.tick_count)
        self.tick_count += 1

