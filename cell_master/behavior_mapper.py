# cell_master/behavior_mapper.py

def map_node_to_intents(node):
    """
    Map a scan node into 1..N intents suitable for per-cell execution.
    Node is a dict created by node_builder.
    Returns a list of intent dicts.
    """

    node_type = node.get("node_type")
    intents = []

    # === STEP3: Antigen_sampling → DC phagocytose + pMHC presentation ===
    if node_type == "Antigen_sampling":
        intents.append({
            "intent_type": "phagocytose",
            "targets": ["DC"],
            "coord": None,
            "meta": {
                "reason": "antigen_sampling",
                "source_node": node["node_id"]
            }
        })

        intents.append({
            "intent_type": "pMHC_presented",
            "targets": ["DC"],
            "coord": None,
            "meta": {
                "epitopes": node["inputs"]["ligand"],
                "source_node": node["node_id"]
            }
        })

        return intents

    # === STEP4: Tcell_activation ===
    if node_type == "Tcell_activation":
        intents.append({
            "intent_type": "activate_tcell",
            "targets": ["Tcell"],
            "coord": node.get("coord"),
            "meta": {
                "mhc_source": node["node_id"],
                "reason": "tcell_activation"
            }
        })
        return intents

    # default fallback
    return []


# Optional: explicit exports
__all__ = ["map_node_to_intents"]

