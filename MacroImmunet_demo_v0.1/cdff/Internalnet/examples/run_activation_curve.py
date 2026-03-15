from Internalnet.engine.graph_loader import load_node_schema
from Internalnet.engine.internalnet_engine import InternalNetEngine
from Internalnet.analysis.plotting import plot_curve

graph = load_node_schema(
    "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
)

engine = InternalNetEngine(graph)

pmhc_values = []
nfat_values = []

for i in range(11):

    pmhc = i / 10

    state = {
        "pMHC": pmhc,
        "energy": 1.0,
        "stress": 0.1
    }

    node_values = state

    for _ in range(8):
        node_values = engine.forward(node_values)

    pmhc_values.append(pmhc)
    nfat_values.append(node_values["NFAT"])

plot_curve(
    pmhc_values,
    nfat_values,
    "pMHC",
    "NFAT activation",
    "TCR Activation Curve"
)
