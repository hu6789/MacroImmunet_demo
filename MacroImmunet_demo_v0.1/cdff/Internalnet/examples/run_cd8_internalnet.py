from Internalnet.engine.graph_loader import load_node_schema
from Internalnet.engine.internalnet_engine import InternalNetEngine


def main():

    graph = load_node_schema(
        "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
    )

    engine = InternalNetEngine(graph)

    state = {
        "pMHC": 1.0,
        "viral_load": 0.3,
        "ATP_level": 1.0,
        "energy": 1.0,
        "stress": 0.1
    }

    new_state = engine.forward(state)

    print("\n===== CD8 T Cell InternalNet Output =====\n")

    for k, v in new_state.items():

        if isinstance(v, float):
            print(f"{k:20s} {v:.3f}")
        else:
            print(f"{k:20s} {v}")


if __name__ == "__main__":
    main()
