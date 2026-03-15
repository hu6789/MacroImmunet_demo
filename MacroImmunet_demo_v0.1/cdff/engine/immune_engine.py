class ImmuneEngine:

    def __init__(self, world, scanmaster, cellmaster, labelcenter):

        self.world = world
        self.scanmaster = scanmaster
        self.cellmaster = cellmaster
        self.labelcenter = labelcenter

    def step(self):

        for cell in self.world.cells:

            node_input = self.scanmaster.scan_cell(cell)

            intents = self.cellmaster.process_cell(cell, node_input)

            for intent in intents:
                self.labelcenter.queue(intent)

        self.labelcenter.apply()
