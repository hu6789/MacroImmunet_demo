class IntentBuilder:

    def __call__(self, cell, result, asi_output):

        intents = []

        behaviors = result.get("behaviors", [])
        fate = result.get("fate")

        # =========================
        # 🔹 1️⃣ Behavior → Intent
        # =========================
        for b in behaviors:

            output = b.get("output", {})
            otype = output.get("type")

            # =========================
            # 🔹 1️⃣ Intent 类型（原逻辑）
            # =========================
            if otype == "intent":

                intent_type = output.get("intent_type")
                target_spec = output.get("target", None)

                target_id = None

                if target_spec == "selected_target":
                    target_id = asi_output.get("selected_target")

                elif target_spec == "self":
                    target_id = cell.cell_id

                elif isinstance(target_spec, int):
                    target_id = target_spec

                # 强度
                if output.get("intensity_source") == "drive":
                    strength = b.get("drive", 0.0)
                else:
                    strength = output.get("value", 1.0)

                strength *= output.get("value", 1.0)

            # =========================
            # 🔹 2️⃣ Field 类型（🔥新增）
            # =========================
            elif otype == "field":

                if output.get("intensity_source") == "drive":
                    strength = b.get("drive", 0.0)
                else:
                    strength = output.get("value", 1.0)

                strength *= output.get("value", 1.0)

                intents.append({
                    "type": "add_field",
                    "field": output.get("field"),
                    "value": strength,
                    "source": cell.cell_id
                })
                
                continue

            intent_type = output.get("intent_type")
            target_spec = output.get("target", None)

            # -------------------------
            # 🎯 target resolution
            # -------------------------
            target_id = None

            if target_spec == "selected_target":
                target_id = asi_output.get("selected_target")

            elif target_spec == "self":
                target_id = cell.cell_id

            elif isinstance(target_spec, int):
                target_id = target_spec

            # -------------------------
            # 🔥 intensity
            # -------------------------
            if output.get("intensity_source") == "drive":
                strength = b.get("drive", 0.0)
            else:
                strength = output.get("value", 1.0)

            # 可选缩放
            strength *= output.get("value", 1.0)

            # -------------------------
            # 🧾 build intent
            # -------------------------
            if intent_type == "damage_cell" and target_id is not None:

                intents.append({
                    "type": "damage_cell",
                    "source": cell.cell_id,
                    "target": target_id,
                    "strength": strength
                })

            elif intent_type == "add_field":

                intents.append({
                    "type": "add_field",
                    "field": output.get("field"),
                    "value": strength,
                    "source": cell.cell_id
                })

        # =========================
        # 🔹 2️⃣ Fate → Intent（统一规范）
        # =========================

        if fate == "dying":

            intents.append({
                "type": "cell_die",
                "target": cell.cell_id
            })

        print("DEBUG behaviors:", result.get("behaviors"))
        return intents
