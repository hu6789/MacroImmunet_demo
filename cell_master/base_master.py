"""
Compatibility shim: re-export the demo CellMasterBase as BaseMaster
so modules expecting `cell_master.base_master.BaseMaster` keep working.
"""
from .cell_master_base import CellMasterBase

# Provide the expected name
BaseMaster = CellMasterBase

__all__ = ["BaseMaster", "CellMasterBase"]
