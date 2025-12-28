# test/test_step5_5_release_label_ownership.py

import pytest
from label_center.label_center_base import LabelCenterBase

__all__ = ["LabelCenterBase"]


def test_release_owned_label():
    lc = LabelCenterBase()

    lc.label_field[(0, 0)] = {
        "antigen": {
            "value": 10.0,
            "last_tick": 0,
            "owned_by": "percell_A"
        }
    }

    lc.release_label(coord=(0, 0), label_name="antigen", by="percell_A")

    assert lc.label_field[(0, 0)]["antigen"]["owned_by"] is None

def test_release_owned_label():
    lc = LabelCenterBase()

    lc.label_field[(0, 0)] = {
        "antigen": {
            "value": 10.0,
            "last_tick": 0,
            "owned_by": "percell_A"
        }
    }

    lc.release_label(coord=(0, 0), label_name="antigen", by="percell_A")

    assert lc.label_field[(0, 0)]["antigen"]["owned_by"] is None

