class Cell:

    def __init__(self, config):
        self.config = config

        # ===== Identity =====
        self.id = None
        self.cell_type = None
        self.position = (0, 0)

        # ===== Core State =====
        self.node_state = config.get("init_node_state", {}).copy()

        # 🔥 HIR 专用状态（关键新增）
        self.state = {
            "labels": [],          # ["stressed", "activated"]
            "fate": "normal"       # normal / dying / apoptotic
        }

        # ===== Params =====
        self.feature_params = {}
        self.receptor_params = {}
        self.behavior_params = {}

        # ===== Capability / Switch =====
        self.capability = config.get("capability", {})

        # 🔥 行为开关（未来很重要）
        self.behavior_switch = config.get("behavior_switch", {})

        # ===== Metadata =====
        self.meta = {}
