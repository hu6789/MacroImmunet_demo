from cellmaster.Internalnet.signal_mapping.mapping_utils import apply_mapping

class InputBuilder:
    # ⚡ 原 INPUT_NODE_MAP 保留 fallback
    INPUT_NODE_MAP = {
        "pMHC_signal": "TCR_receptor",
        "costim_external": "costim_receptor",
        "IFN_external": "IFN_receptor"
    }

    def build(self, cell, scan_output, asi_output):
        external_field = {}

        # ✅ contact signals
        contacts = scan_output.get("cell_contacts", [])
        pMHC_signal = costim_signal = 0.0
        for c in contacts:
            pMHC_signal = max(pMHC_signal, c.get("pMHC", 0.0))
            costim_signal = max(costim_signal, c.get("costim", 0.0))
        external_field["pMHC_signal"] = pMHC_signal
        external_field["costim_external"] = costim_signal

        # ✅ field signals
        for k, v in scan_output.get("ligand_summary", {}).items():
            external_field[k] = v

        # ✅ ASI signals
        for k, v in asi_output.get("signals", {}).items():
            external_field[k] = external_field.get(k, 0.0) + v

        # =========================
        # 🔥 NEW: use Signal Mapping Library
        # =========================
        node_input = apply_mapping(external_field, {})

        # 🔥 fallback: INPUT_NODE_MAP 保留旧逻辑
        for ext_key, node_name in self.INPUT_NODE_MAP.items():
            if ext_key in external_field and node_name not in node_input:
                node_input[node_name] = external_field[ext_key]

        # debug
        print("INPUT to net:", external_field)
        print("MAPPED node_input:", node_input)
        print("FINAL node_input keys:", list(node_input.keys()))
        return node_input
