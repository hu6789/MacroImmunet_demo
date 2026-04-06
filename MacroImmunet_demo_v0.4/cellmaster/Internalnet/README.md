# MacroImmunet – InternalNet (v0.4)

## Overview

**InternalNet** is the intracellular decision-making module in the MacroImmunet framework.
It models how individual cells process signals, regulate internal state, and generate behavioral intents.

This version (v0.4) establishes a **clean separation of concerns** between:

* Environmental sensing (ScanMaster)
* Intracellular decision-making (InternalNet)
* Action realization (CDFF / IntentBuilder)
* World state updates (LabelCenter)

---

## Architecture

```
ScanMaster → external_field → InternalNet → behaviors → CDFF / IntentBuilder → World
```

### Components

#### 1. ScanMaster (external)

* Detects spatial context (ROI, hotspots, contacts)
* Produces **environmental signals**
* Does NOT modify cell internal state directly

#### 2. InternalNet (this module)

* Processes signals via node graph
* Applies physiological constraints via HIR
* Generates behavior candidates (intents)

#### 3. CDFF / IntentBuilder (downstream)

* Converts behaviors into executable intents
* Handles targeting, quantities, and ownership

#### 4. World / LabelCenter (external)

* Applies intents to global state (fields, cells, particles)

---

## InternalNet Pipeline

Each simulation tick:

```
1. Node Update (signal processing)
2. HIR (feasibility & fate decision)
3. Behavior Evaluation (intent generation)
4. State Update (internal feedback)
```

---

## Node System

### Purpose

Nodes represent intracellular signals and processes:

* receptors (e.g. IFN_receptor, TCR_receptor)
* signaling pathways (NFkB, IRF3)
* stress and damage
* metabolic state
* effector programs

---

### Node Categories

| Type     | Description               |
| -------- | ------------------------- |
| sensor   | Reads from external_field |
| internal | Regular signaling node    |
| emitter  | Outputs to external_field |

---

### Example Node

```json
{
  "node_id": "IFN_receptor",
  "io_role": "sensor",
  "external_key": "IFN_external",
  "update_rule": "direct_input"
}
```

---

### Update Rules

Supported rules:

* `weighted_sum`
* `sigmoid`
* `threshold`
* `inverse_signal`
* `logic_gate` (v0.4)

---

### Logic Gate (NEW in v0.4)

```json
{
  "update_rule": "logic_gate",
  "inputs": ["activation_signal", "costim_signal"],
  "params": {
    "type": "AND",
    "threshold": 0.5
  }
}
```

Used for **co-stimulation and strict activation requirements**.

---

## Activation Model (v0.4)

### Design Principle

* Activation is **continuous**
* Effector commitment is **discrete (gated)**

---

### Signal Flow

```
TCR_receptor  → \
                 → activation_signal (continuous, sigmoid)
costim_signal → /

activation_signal + costim_signal
        ↓ (AND gate)
cytotoxic_program
```

---

### Interpretation

* Signal 1: antigen recognition (TCR / pMHC)
* Signal 2: context / danger (cytokines, IFN)

Both are required for full effector activation.

---

## Behavior System

### Role

Behaviors represent **intent-level actions**, not direct execution.

---

### Example: kill_target

```json
{
  "behavior_id": "kill_target",
  "gate": [
    { "node": "cytotoxic_program", "threshold": 0.5 }
  ],
  "output": {
    "type": "cell_interaction",
    "target": "kill"
  }
}
```

---

### Important

* Behaviors do NOT modify other cells directly
* They produce **intents** to be consumed by CDFF

---

## HIR (Homeostatic / Integrity Regulator)

HIR is an internal constraint system that:

* Evaluates physiological feasibility
* Suppresses invalid behaviors
* Determines cell fate (normal, stressed, dying, etc.)

HIR has **final authority on viability**, but does not generate actions.

---

## External Field Interface (Critical for Integration)

### Definition

`external_field` is the only interface between:

* ScanMaster ↔ InternalNet
* InternalNet ↔ environment

---

### Example

```json
{
  "IFN_external": 0.8,
  "TNF_external": 0.2,
  "pMHC_signal": 1.0
}
```

---

### Mapping Rule

Each receptor node defines:

```json
"external_key": "IFN_external"
```

👉 ScanMaster MUST output matching keys.

---

### Data Flow

```
ScanMaster → external_field → receptor nodes → node graph
node emitters → external_field → environment
```

---

## Simulation Loop (Simplified)

```
for each tick:
    1. decay external_field
    2. update nodes (read environment)
    3. collect emitters (write environment)
    4. evaluate behaviors + HIR
    5. update internal state
```

---

## Current Limitations (v0.4)

* ❗ No world interaction (behaviors do not affect other cells yet)
* ❗ No spatial modeling (signals are global, not local)
* ❗ No target binding (kill_target has no resolved target)
* ❗ IntentBuilder not yet integrated

These are handled in downstream modules (CDFF / LabelCenter).

---

## Design Philosophy

InternalNet follows strict separation:

| Layer      | Responsibility     |
| ---------- | ------------------ |
| Node Graph | Signal dynamics    |
| HIR        | Feasibility / fate |
| Behavior   | Intent generation  |
| CDFF       | Action realization |
| World      | State update       |

---

## Future Work

* Integration with CDFF / IntentBuilder
* Spatially-aware ScanMaster input
* Target resolution for interactions
* Multi-cell coordination
* Advanced co-stimulation pathways

---

## Summary

InternalNet v0.4 provides:

* A modular intracellular signaling framework
* A clean interface to external environment (external_field)
* A separation between decision and execution
* A foundation for scalable immune simulation

It is designed to be **plug-compatible with CDFF and world simulation layers**.

