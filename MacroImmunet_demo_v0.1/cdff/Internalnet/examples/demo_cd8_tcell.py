from Internalnet.engine.graph_loader import load_node_schema
from Internalnet.engine.internalnet_engine import InternalNetEngine
from Internalnet.behavior.behavior_engine import BehaviorEngine
from Internalnet.hir.hir_engine import HIREngine


graph = load_node_schema(
    "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
)

engine = InternalNetEngine(graph)
hir_engine = HIREngine()
behavior_engine = BehaviorEngine()

state = {
    "pMHC": 0.8,
    "energy": 1.0,
    "stress": 0.1
}

node_values = state

# signaling propagation
for _ in range(8):
    node_values = engine.forward(node_values)

# HIR evaluation
hir = hir_engine.evaluate(node_values)

# behavior decision
behaviors = behavior_engine.generate(node_values, hir)

print("\nRaw signaling nodes:")
for k, v in node_values.items():
    if isinstance(v, float):
        print(k, round(v, 3))

print("\nHIR result:")
print(hir)

print("\nFinal behaviors:")
print(behaviors)
