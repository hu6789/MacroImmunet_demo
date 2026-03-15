import json


class StageTrace:

    def __init__(self):

        self.scan = None
        self.node_input = None
        self.asi_output = None
        self.internalnet_output = None
        self.hir_result = None
        self.intents = None

    def show(self):

        print("========== TRACE ==========")

        if self.scan:
            print("\nSCAN")
            print(json.dumps(self.scan, indent=2))

        if self.node_input:
            print("\nNODE INPUT")
            print(json.dumps(self.node_input, indent=2))

        if self.asi_output:
            print("\nASI OUTPUT")
            print(json.dumps(self.asi_output, indent=2))

        if self.internalnet_output:
            print("\nINTERNALNET")
            print(json.dumps(self.internalnet_output, indent=2))

        if self.hir_result:
            print("\nHIR RESULT")
            print(json.dumps(self.hir_result, indent=2))

        if self.intents:
            print("\nINTENTS")
            print(json.dumps(self.intents, indent=2))
