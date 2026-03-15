class IntentBuilder:
    """
    将 behaviors 转换为 atomic intents
    """

    def build(self, cell, behaviors):
        intents = []

        for b in behaviors:

            if isinstance(b, dict):
                intent_type = b.get("type")
                target = b.get("target")
            else:
                intent_type = b
                target = None

            intent = {
                "type": intent_type,
                "source": cell["id"],
                "target": target,
                "payload": {},
                "meta": {
                    "cell_id": cell["id"],
                    "cell_master": cell.get("master"),
                    "engine": "MiniNet"
                }
            }

            intents.append(intent)

        return intents

    def build_intent(self, cell, behavior):
        """
        新加单个行为构建接口，兼容 build_intents
        """
        # 把单个行为包装成 list 调用 build
        return self.build(cell, [behavior])[0]

    def build_intents(self, cell, behaviors):
        """
        Compatibility wrapper for CellMaster.
        """
        intents = []

        for b in behaviors.get("behaviors", []):
            intent = self.build_intent(cell, b)
            if intent:
                intents.append(intent)

        return intents
