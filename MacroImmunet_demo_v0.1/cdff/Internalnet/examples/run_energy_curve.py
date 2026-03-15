from Internalnet.engine.graph_loader import load_node_schema
from Internalnet.engine.internalnet_engine import InternalNetEngine
from Internalnet.hir.hir_engine import HIREngine
from Internalnet.behavior.behavior_engine import BehaviorEngine
from Internalnet.analysis.plotting import plot_curve


graph = load_node_schema(
    "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
)

engine = InternalNetEngine(graph)
hir_engine = HIREngine()
behavior_engine = BehaviorEngine()

energy_values = []
prolif_values = []

for i in range(11):

    energy = i / 10

    state = {
        "pMHC": 0.8,
        "energy": energy,
        "stress": 0.1
    }

    node_values = state

    for _ in range(8):
        node_values = engine.forward(node_values)

    hir = hir_engine.evaluate(node_values)

    behaviors = behavior_engine.generate(node_values, hir)

    energy_values.append(energy)

    if "proliferate" in behaviors:
        prolif_values.append(1)
    else:
        prolif_values.append(0)

plot_curve(
    energy_values,
    prolif_values,
    "Energy",
    "Proliferation",
    "Energy Threshold for Proliferation"
)
