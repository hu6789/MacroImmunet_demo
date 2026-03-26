HIR — Homeostatic / Integrity Regulator



The HIR module represents a constraint-aware physiological regulator embedded within the InternalNet pipeline.



It evaluates whether cellular behaviors are biologically feasible under current internal conditions.



Functional Roles



HIR performs three core functions:



1\. Fate Determination



Computes continuous scores and assigns discrete cell states:



normal / stressed / dying

2\. Constraint Enforcement



Applies hard or semi-hard constraints:



disables incompatible behaviors (e.g. division under dying state)

suppresses outputs under extreme stress

3\. Behavior Modulation



Provides group-level modulation signals:



group\_modifiers ∈ \[0, 1.5]



These signals scale behavior outputs in a continuous manner.



Design Principles

HIR does not generate behaviors

HIR does not modify node dynamics

HIR only filters and modulates behavior outcomes

Input



HIR operates on aggregated physiological features:



features = {

&#x20; energy,

&#x20; stress,

&#x20; damage,

&#x20; viral\_load,

&#x20; ...

}

Output

{

&#x20; "fate": str,

&#x20; "scores": dict,

&#x20; "group\_modifiers": dict,

&#x20; "blocks": dict

}

Key Property

HIR rules are global and consistent across cells,

while outcomes vary based on each cell's internal state.

