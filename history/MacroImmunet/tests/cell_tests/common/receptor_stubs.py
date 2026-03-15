# tests/cell_tests/common/receptor_stubs.py
"""
Simple receptor stubs for unit tests.

Provides:
 - ReceptorStub: object with .read(env=None, position=None) -> numeric
 - make_receptor_stub(mapping): mapping name->value => dict name->ReceptorStub
"""
from typing import Any, Dict

class ReceptorStub:
    def __init__(self, value: Any = 0.0):
        # value can be numeric or a callable for more complex behavior
        self._value = value

    def read(self, env=None, position=None):
        # If _value is callable, call it with (env, position)
        if callable(self._value):
            try:
                return float(self._value(env, position))
            except Exception:
                return 0.0
        try:
            return float(self._value)
        except Exception:
            return 0.0

def make_receptor_stub(mapping: Dict[str, Any]):
    """
    mapping: dict like {'IL2': 10.0, 'TCR': 0.8}
    returns: dict {'IL2': ReceptorStub(10.0), ...}
    """
    return {name: ReceptorStub(val) for name, val in mapping.items()}
