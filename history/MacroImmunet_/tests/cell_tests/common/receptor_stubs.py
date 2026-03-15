# tests/cell_tests/common/receptor_stubs.py
"""
Small receptor helper functions for unit tests.
These are intentionally simple reference implementations to allow testing
receptor -> downstream behavior chains without full engine.
"""
import math

def simple_receptor_bound_count(ligand_level, params):
    """
    Simple equilibrium approx: bound = R * (k_on * L) / (k_off + k_on * L)
    params: dict with keys 'k_on','k_off','count'
    """
    k_on = float(params.get('k_on', 0.01))
    k_off = float(params.get('k_off', 0.02))
    R = float(params.get('count', 1))
    denom = (k_off + k_on * float(ligand_level))
    if denom <= 0:
        return 0.0
    frac = (k_on * ligand_level) / denom
    return R * frac

def integrate_with_decay(prev_integral, new_bound, window_ticks):
    if window_ticks <= 0:
        return new_bound
    decay = math.exp(-1.0 / float(window_ticks))
    return prev_integral * decay + new_bound

