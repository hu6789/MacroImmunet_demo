from cdff.scanmaster.scan_master import ScanMaster
from cdff.cellmaster.cell_master import CellMaster
from cdff.engine.immune_engine import ImmuneEngine
from cdff.label_center.label_center import LabelCenter
from cdff.demo.demo_world import DemoWorld


def test_engine_runs_one_step():

    world = DemoWorld()

    scanmaster = ScanMaster(world)
    cellmaster = CellMaster()
    labelcenter = LabelCenter()

    engine = ImmuneEngine(
        world,
        scanmaster,
        cellmaster,
        labelcenter
    )

    engine.step()

    # 如果没有异常说明系统跑通
    assert True
