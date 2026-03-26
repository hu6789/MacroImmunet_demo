class Cell:
    def __init__(self, cell_id, cell_type):

        # 🔹 身份
        self.cell_id = cell_id
        self.cell_type = cell_type

        # 🔹 内部状态（InternalNet唯一读写）
        self.node_state = {
            "IRF3": 0.7,
            "NFkB": 0.6,
            "STAT1": 0.0,
            ...
        }

        # 🔹 生理状态（给 HIR 用，可从 node_state映射）
        self.cell_state = {
            "ATP": 0.6,
            "stress": 0.3,
            "damage": 0.2,
            "viral_RNA": 0.7
        }

        # 🔹 感受器参数（很关键！！）
        self.receptor_profile = {
            "IFN_receptor": 0.8,
            "TNF_receptor": 0.6
        }

        # 🔹 分泌 / 行为能力（给 IntentBuilder 用）
        self.capability = {
            "secretion_capacity": 1.0,
            "IFN_sensitivity": 0.9
        }

        # 🔹 meta（调试 / future）
        self.meta = {
            "alive": True,
            "age": 0
        }
