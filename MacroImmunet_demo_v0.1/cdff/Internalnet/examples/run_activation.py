from Internalnet.engine.graph_loader import load_node_schema
from Internalnet.engine.internalnet_engine import InternalNetEngine


def main():

    graph = load_node_schema(
        "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
    )

    print("\n===== T Cell Activation Curve (Debug) =====\n")

    header = [
       "pMHC",
        "TCR",
        "Lck",
        "ZAP70",
        "LAT",
        "PLCg",
        "Ca_signal",
        "NFAT"
    ]

    print(" ".join(f"{h:>10}" for h in header))

    for i in range(11):

        pmhc = i / 10.0

        state = {
            "pMHC": pmhc,
            "energy": 1.0,
            "stress": 0.1
        }

        engine = InternalNetEngine(graph)

        new_state = state

        for _ in range(8):
            new_state = engine.forward(new_state)

        row = [
            pmhc,
            new_state.get("TCR", 0),
            new_state.get("Lck", 0),
            new_state.get("ZAP70", 0),
            new_state.get("LAT", 0),
            new_state.get("PLCg", 0),
            new_state.get("Ca_signal", 0),
            new_state.get("NFAT", 0)
        ]
        print(" ".join(f"{v:10.3f}" for v in row))


if __name__ == "__main__":
    main()
