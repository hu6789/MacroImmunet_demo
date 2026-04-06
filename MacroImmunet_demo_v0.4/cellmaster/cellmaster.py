# cellmaster/cellmaster.py

class CellMaster:

    def __init__(self, internal_net, asi, input_builder, intent_builder):
        self.internal_net = internal_net
        self.asi = asi
        self.input_builder = input_builder
        self.intent_builder = intent_builder

    def step(self, cell, world, scan_output):

        # =========================
        # 1️⃣ ASI（抗原/受体解释层）
        # =========================
        if self.asi:
            asi_output = self.asi.run(cell, scan_output)
        else:
            asi_output = {
                "signals": {},
                "selected_target": 4,
                "match_score": 0.0
            }

        # =========================
        # 2️⃣ External Field（NodeInput构建）
        # =========================
        if self.input_builder:
            external_field = self.input_builder.build(
                cell,
                scan_output,
                asi_output
            )
        else:
            external_field = {}

        # =========================
        # 3️⃣ InternalNet（核心决策）
        # =========================
        result = self.internal_net.step(cell, external_field)

        # =========================
        # 4️⃣ IntentBuilder（行为落地）
        # =========================
        intents = self.intent_builder(
            cell,
            result,
            asi_output   # 🔥 用 ASI，不用 external_field
        )
        
        print("SCAN ligand:", scan_output.get("ligand_summary"))

        return intents, result, external_field
