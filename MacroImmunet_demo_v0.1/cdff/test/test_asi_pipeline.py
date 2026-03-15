from cdff.cellmaster.cell_master import CellMaster


def test_asi_pipeline():

    cell_master = CellMaster()

    event = {
        "epitopes": [
            {"epitope_id": "E1"}
        ]
    }

    cell_state = {
        "receptors": [
            {"receptor_id": "TCR1"}
        ]
    }

    behaviors = cell_master.decide(event, cell_state)

    assert isinstance(behaviors, list)
