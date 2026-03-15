from cdff.intent.intent_validator import validate_intent

class LabelCenter:

    def __init__(self):
        # 用于存放 intent 队列
        self.intent_queue = []
        # 存放按 cell_id 索引的最终世界状态（简单演示用）
        self.state = {}

    def queue(self, intent):
        # 校验合法性
        if validate_intent(intent):
            self.intent_queue.append(intent)
        else:
            print(f"[LabelCenter] Invalid intent skipped: {intent}")

    def apply(self, intents=None):
        """
        写入 LabelCenter。
        如果传入 intents，则直接写入，否则清空 intent_queue（原接口兼容）。
        """
        if intents is not None:
            for intent in intents:
                cell_id = intent.get("cell_id", None)
                if cell_id:
                    self.state[cell_id] = intent
        # 清空队列（保持旧行为）
        self.intent_queue.clear()

    def state_summary(self):
        """
        返回当前 LabelCenter 的状态快照
        """
        return self.state
