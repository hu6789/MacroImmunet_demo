def build_hir_features(node_state, params):

    return {
        "energy": params.get("energy_from_ATP", 1.0)
                  * node_state.get("ATP", 0.5),

        "stress": params.get("stress_sensitivity", 1.0) * (
            0.6 * node_state.get("stress", 0.0)
            + 0.4 * node_state.get("ROS", 0.0)
        ),

        "damage": params.get("damage_sensitivity", 1.0)
                  * node_state.get("damage", 0.0),

        "viral_load": node_state.get("viral_RNA", 0.0)
    }
