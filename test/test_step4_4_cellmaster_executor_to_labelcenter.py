from cell_master.cell_master_base import CellMasterBase
from cell_master.executor import DefaultIntentExecutor
from label_center.label_center_base import LabelCenterBase


def test_step4_4_7_executor_enqueue_labelcenter():
    lc = LabelCenterBase()
    executor = DefaultIntentExecutor(label_center=lc)

    cm = CellMasterBase(
        executor=executor,
        budget=1,
        score_threshold=1.0
    )

    node = {
        "meta": {"coord": (3, 3)},
        "score": 4.2,
    }

    cm.process_nodes([node])

    assert len(lc.request_queue) == 1
    intent = lc.request_queue[0]
    assert intent["name"] == "emit_label"
    assert intent["payload"]["coord"] == (3, 3)

