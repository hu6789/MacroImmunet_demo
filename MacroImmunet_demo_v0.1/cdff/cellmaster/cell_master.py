from cdff.intentbuilder.intent_builder import IntentBuilder
from cdff.Internalnet.Internal_net import InternalNet

from cdff.asi.asi import AdaptiveSpecificityInterpreter as ASI
from cdff.asi.asi_adapter import ASIAdapter

from cdff.Internalnet.hir.hir_engine import HIREngine as HIR
class CellMaster:
    def __init__(self,
                 internalnet=None,
                 asi=None,
                 hir=None,
                 intent_builder=None):

        adapter = ASIAdapter()

        self.asi = asi or ASI(adapter)
        self.internalnet = internalnet or InternalNet()
        self.hir = hir or HIR()
        self.intent_builder = intent_builder or IntentBuilder()
    def decide(self, event, cell_state):
        asi_result = self.asi.run(
            raw_input=event,
            source=event.get("source", "test"),
            receptors=cell_state.get("receptors", []),
            cell_context=cell_state,
            decision_input=event
        )

        behaviors = self.internalnet.step(
            cell_state,
            asi_result
        )

        filtered = self.hir.filter_behaviors(
            cell_state,
            behaviors
        )

        return behaviors.get("behaviors", [])

    def process_cell(self, cell, node_input):

        asi_result = self.asi.run(
            raw_input=node_input,
            source="scanmaster",
            receptors=cell.get("receptors", []),
            cell_context=cell,
            decision_input=node_input
        )

        behaviors = self.internalnet.step(
            cell,
            asi_result
        )

        filtered = self.hir.filter_behaviors(
            cell,
            behaviors
        )

        intents = self.intent_builder.build_intents(
            cell,
            filtered
        )

        return intents
