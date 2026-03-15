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

stress_values = []
il2_values = []

for i in range(11):

    stress = i / 10

    state = {
        "pMHC": 0.8,
        "energy": 1.0,
        "stress": stress
    }

    node_values = state

    for _ in range(8):
        node_values = engine.forward(node_values)

    hir = hir_engine.evaluate(node_values)

    behaviors = behavior_engine.generate(node_values, hir)

    stress_values.append(stress)
    il2_values.append(node_values["IL2"])

plot_curve(
    stress_values,
    il2_values,
    "Stress",
    "IL2 production",
    "Stress Suppression Curve"
)
