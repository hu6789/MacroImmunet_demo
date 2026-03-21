Behavior System Specification (v0.2)
1. Overview

The Behavior System defines how intracellular signals are translated into cellular actions.

It serves as the bridge between:

Node Network (signal state)
        ↓
Behavior Evaluation (this layer)
        ↓
HIR (feasibility modulation)
        ↓
IntentBuilder (world action execution)
2. Design Principles
1. Separation of concerns:
   - Node: signal computation only
   - Behavior: signal → action mapping
   - HIR: physiological feasibility control
   - Cell: individual variability

2. Behavior does NOT:
   - write world state
   - decide fate (HIR does)

3. Behavior MUST be:
   - declarative (JSON-driven)
   - composable
   - extensible
3. Behavior Execution Pipeline
For each cell (per tick):

1. Evaluate gate conditions
2. Compute drive (from node values)
3. Apply cell intrinsic scaling
4. Apply HIR modulation
5. Compute activation (threshold / probability)
6. Select behaviors (based on selection_mode)
7. Output behavior → IntentBuilder
4. Behavior JSON Schema
4.1 Full Structure
{
  "behavior_id": "string",

  "category": "secretion | stress_response | metabolism | fate_related | other",

  "selection_mode": "independent | exclusive | competitive",

  "gate": [
    {
      "node": "string",
      "threshold": "float"
    }
  ],

  "drive": {
    "type": "weighted_sum | product | custom",
    "inputs": [
      { "node": "string", "weight": "float" }
    ],
    "formula": "optional (for custom)"
  },

  "activation": {
    "mode": "deterministic | probabilistic",
    "threshold": "float",
    "slope": "float (optional, for probabilistic)"
  },

  "cell_influence": {
    "sensitivity_param": "string",
    "capacity_param": "string (optional)"
  },

  "hir_interaction": {
    "use_global_scale": "bool",
    "use_modifier": "bool",
    "blockable": "bool"
  },

  "output": {
    "type": "secretion | internal_state | signal",
    "target": "string",
    "intensity_source": "drive | fixed | custom"
  }
}
5. Key Concepts
5.1 Gate (Precondition)
Gate determines whether a behavior is eligible for evaluation.

If ANY gate condition fails:
→ behavior is skipped entirely

Example:

"gate": [
  { "node": "IRF3", "threshold": 0.2 }
]
5.2 Drive (Signal Integration)
Drive represents the activation strength of a behavior.

It is computed from node values.
Supported types:
weighted_sum   → linear combination
product        → AND-like synergy
custom         → user-defined formula
5.3 Activation
Determines whether the behavior actually triggers.
Modes:

Deterministic

trigger if drive > threshold

Probabilistic

P = sigmoid(slope * (drive - threshold))
5.4 Selection Mode (Critical)

Controls interaction between behaviors.

independent
Multiple behaviors can occur simultaneously
exclusive
Only one behavior in the group can occur
(e.g. apoptosis vs survival)
competitive
Behaviors compete based on drive
(e.g. softmax selection)
5.5 Cell Influence (Heterogeneity Layer)
Cell-specific parameters modulate behavior strength

Applied as:

drive *= cell[sensitivity_param]

Examples:

IFN_sensitivity
secretion_capacity
stress_tolerance
5.6 HIR Interaction (Post-Processing)

HIR modifies behavior AFTER drive computation.

Applied as:

drive *= HIR.global_scale
drive *= HIR.modifier[behavior_id]

if behavior_id in HIR.block:
    drive = 0
5.7 Output Mapping

Defines how behavior translates into Intent.

"output": {
  "type": "secretion",
  "target": "IFN",
  "intensity_source": "drive"
}
6. Example Behavior
secrete_IFN
{
  "behavior_id": "secrete_IFN",

  "category": "secretion",

  "selection_mode": "independent",

  "gate": [
    { "node": "IRF3", "threshold": 0.2 }
  ],

  "drive": {
    "type": "weighted_sum",
    "inputs": [
      { "node": "IRF3", "weight": 0.6 },
      { "node": "NFkB", "weight": 0.3 },
      { "node": "STAT1", "weight": 0.2 }
    ]
  },

  "activation": {
    "mode": "probabilistic",
    "threshold": 0.5,
    "slope": 4.0
  },

  "cell_influence": {
    "sensitivity_param": "IFN_sensitivity"
  },

  "hir_interaction": {
    "use_global_scale": true,
    "use_modifier": true,
    "blockable": true
  },

  "output": {
    "type": "secretion",
    "target": "IFN",
    "intensity_source": "drive"
  }
}

