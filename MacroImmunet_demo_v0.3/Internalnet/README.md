InternalNet — Cell Decision Engine

Overview



The InternalNet module implements the cell-intrinsic decision system, transforming environmental inputs into:



internal state updates

behavior activations

fate outcomes (via HIR)

🔁 Execution Pipeline



Each step follows:



node\_input → node graph → HIR → behavior → state update

1️⃣ Node System (Signal Dynamics)

Structure



Defined by:



node/graph/graph\_v0.2.json

node/defs/\*.json



Example:



{

&#x20; "node\_id": "IFN\_signal",

&#x20; "inputs": \["IRF3", "NFkB"],

&#x20; "update\_rule": "weighted\_sum",

&#x20; "params": {

&#x20;   "weights": \[1.0, 0.8]

&#x20; },

&#x20; "decay\_tau": 4.0

}

Execution



Handled by:



run\_node\_graph(node\_state)

Supported Update Rules

weighted\_sum

threshold

inverse\_signal

baseline

external

Key Properties

Iterative update (steps=3)

bounded state (0 \~ 1)

optional temporal smoothing via decay\_tau

2️⃣ Input Integration (Scan → Node)



External signals are injected into node state:



node\_state\[k] = 0.9 \* prev + v / (1 + v)



Additionally, nonlinear gating is supported:



IFN\_eff > threshold → amplified response

3️⃣ HIR (Constraint \& Fate Layer)



HIR operates on aggregated physiological features:



features = build\_hir\_features(node\_state, cell.feature\_params)

hir\_output = compute\_HIR(features)

HIR Outputs

{

&#x20; "fate": "normal | stressed | dying",

&#x20; "scores": {...},

&#x20; "group\_modifiers": {...},

&#x20; "blocks": {...}

}

Functional Roles



HIR provides:



fate determination

hard constraints (blocks)

group-level modulation signals

4️⃣ Behavior System (Action Formation)



Defined in:



behavior/\*.json



Example:



{

&#x20; "behavior\_id": "secrete\_IFN",

&#x20; "group": "cytokine\_secretion",

&#x20; "drive": {

&#x20;   "inputs": \[...]

&#x20; },

&#x20; "activation": {

&#x20;   "mode": "probabilistic"

&#x20; }

}

Execution

evaluate\_behaviors(node\_state, hir\_output, behaviors)

Behavior Pipeline

Gate check

Drive computation

HIR modulation

Activation (deterministic / probabilistic)

Output filtering

5️⃣ HIR Interaction



Behaviors can interact with HIR via:



"hir\_interaction": {

&#x20; "use\_modifier": true,

&#x20; "use\_global\_scale": true,

&#x20; "blockable": true

}

Effects

block → strong suppression (not hard zero)

modifier → continuous scaling

6️⃣ State Update (Feedback Loop)



After behavior execution:



apply\_state\_update(node\_state, behavior\_outputs)

Example

"state\_effects": {

&#x20; "ATP": -0.08,

&#x20; "stress": 0.05

}

Role

behavior → modifies internal physiology → affects next step

Design Principles

1\. Separation of Dynamics and Decision

node graph → internal dynamics

behavior → action layer

HIR → constraint layer

2\. Continuous + Discrete Hybrid

node / behavior → continuous

fate / blocks → discrete

3\. Extensibility via JSON

nodes

behaviors

graph

Notes

HIR currently uses continuous modulation (subject to refinement)

node graph topology is static per simulation

no stochastic noise injected at node level (yet)

