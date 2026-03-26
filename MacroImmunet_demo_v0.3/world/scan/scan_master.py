class ScanMaster:

    def __init__(self, label_center, space):
        self.label_center = label_center
        self.space = space

    def scan(self, cell):

        node_input = {}

        node_input.update(self._scan_global())
        node_input.update(self._scan_local(cell))

        return node_input

    def _scan_global(self):
        return {
            "IFN_external": self.label_center.get_field("IFN"),
            "damage": self.label_center.get_field("damage"),
            "viral_RNA": self.label_center.get_field("virus")
        }

    def _scan_local(self, cell):

        pos = self.space.get_cell_pos(cell.cell_id)

        local_IFN = self.space.get_local_field(pos, "IFN")
        global_IFN = self.label_center.get_field("IFN")

        return {
            "local_IFN": local_IFN,
            "IFN_effective": 0.7 * local_IFN + 0.3 * global_IFN
        }
