当然可以，这一版我会按**GitHub README / SPEC 文档风格**来写：
👉 结构清晰
👉 术语统一
👉 可以直接放 repo（甚至作为 v0.4 core spec）

# 📘 MacroImmunet v0.4

## 🔬 InternalNet Core Specification

---

## 🧭 Overview

The **InternalNet system** defines the internal decision-making and physiological dynamics of a single cell.

It is composed of four tightly coupled layers:

```text
Node → HIR → Behavior → State Update → Cell
```

Each layer has a strictly defined responsibility to ensure:

* ✅ biological plausibility
* ✅ architectural modularity
* ✅ simulation consistency

---

## 🔄 Execution Pipeline (Per Tick)

The following execution order is **mandatory**:

```text
1. Node Update (physiological state evolution)
2. HIR Evaluation (state + fate decision)
3. Behavior Evaluation (candidate actions)
4. HIR Modulation (behavior filtering/scaling)
5. Output Generation
   ├─ Internal → update_state
   └─ External → IntentBuilder
6. State Commit (apply merged updates)
```

---

# 🧬 1. Node Layer

---

## 🧠 Definition

Nodes represent **intrinsic cellular variables**:

```text
ATP, stress, receptor activation, signaling states, etc.
```

They are:

* continuous-valued
* updated every tick
* non-decisional

---

## 🧩 Node Classification

### 1. Functional Group

Human-readable module grouping:

```json
"functional_group": "TCR_signaling | metabolism | stress_response"
```

---

### 2. Structural Type

```json
"structural_type": "receptor | ligand | internal"
```

| Type     | Description                    |
| -------- | ------------------------------ |
| receptor | receives external signals      |
| ligand   | exposes signals to environment |
| internal | hidden internal variable       |

---

### 3. IO Role

```json
"io_role": "sensor | emitter | internal"
```

---

### 4. State Class (Dynamics)

```json
"state_class": "transient | stable | accumulative"
```

---

### 5. HIR Role (🔥 critical)

```json
"hir_role": {
  "as_input": true,
  "as_gate": false,
  "as_reference": true
}
```

Defines how a node participates in HIR:

| Role         | Meaning                       |
| ------------ | ----------------------------- |
| as_input     | contributes to HIR evaluation |
| as_gate      | used in fate thresholds       |
| as_reference | used as normalization/scale   |

---

## ⚙️ Node Dynamics

Each node follows a unified update rule:

```text
node_next =
    decay(node_current)
  + input_update
  + behavior_contribution (delayed)
```

---

### Required Parameters

```json
"baseline": 0.0,
"decay_tau": 1.0
```

* `baseline`: resting value
* `decay_tau`: exponential decay factor

---

# 🧠 2. HIR Layer (Homeostatic Integrity Regulator)

---

## 🧭 Definition

HIR is the **central physiological regulator** of the cell.

It is the only component that can:

* evaluate cell health
* determine fate
* modulate behavior

---

## 🧩 Responsibilities

---

### 1. State Evaluation

```text
Inputs:
  ATP, stress, damage, etc.

Outputs:
  state_labels
```

Example:

```text
normal, stressed, exhausted, dying
```

---

### 2. Fate Decision

```text
fate_actions:
  apoptosis
  necrosis
```

---

### 3. Behavior Modulation (🔥 core)

HIR can:

```text
✔ block behaviors
✔ scale behavior intensity
✔ bias activation thresholds
```

---

## ⚠️ Constraints

```text
HIR MUST NOT:
✘ modify node values directly
✘ generate intents
✘ alter network topology
```

---

## 💾 State Storage (Recommended)

```python
cell.state = {
    "labels": [...],
    "fate": "normal | dying | ..."
}
```

---

# ⚡ 3. Behavior Layer

---

## 🧠 Definition

Behaviors are **conditional action generators**.

They are triggered based on node states and produce:

* internal state updates
* external actions

---

## 🔄 Execution Flow

```text
1. Gate check
2. Drive computation
3. Activation decision
4. HIR modulation
5. Output generation
```

---

## 🧩 Key Components

---

### Gate (Execution Condition)

```json
"gate": [
  { "node": "TCR_signal", "threshold": 0.3 }
]
```

* determines if behavior is allowed
* does NOT affect intensity

---

### Drive (Intensity Function)

```json
"drive": {
  "type": "weighted_sum",
  "inputs": [
    { "node": "TCR_signal", "weight": 0.8 },
    { "node": "IFN_signal", "weight": 0.2 }
  ]
}
```

Defines behavior strength.

---

### Activation

```json
"activation": {
  "mode": "deterministic | stochastic",
  "threshold": 0.4,
  "probability": 1.0
}
```

---

### HIR Interaction

```json
"hir_interaction": {
  "blockable": true,
  "scalable": true,
  "modifiable": true
}
```

---

## 🌍 Effect Scope (🔥 required)

```json
"effect_scope": "internal | external"
```

---

## 📤 Output Definition

```json
"output": {
  "type": "internal_state | intent | field | fate",
  "target": "string",
  "intensity_source": "drive | constant",
  "value": 1.0,
  "merge_mode": "add | set | multiply"
}
```

---

## ⚠️ Merge Mode (critical)

When multiple behaviors affect the same target:

```text
add       → accumulation
set       → overwrite
multiply  → scaling
```

Without this → undefined conflicts.

---

# 🔄 4. State Update Layer

---

## 🧠 Definition

A **synchronization layer** that merges all updates before committing to the cell.

---

## 🔄 Execution Order

```text
1. Node intrinsic update
2. Collect behavior outputs
3. Merge (by merge_mode)
4. Write back to node_state
```

---

## ⚠️ Principles

```text
✔ Behavior updates are delayed (not immediate)
✔ Node update and behavior update are separated
✔ All writes are resolved in one place
```

---

# 🧬 5. Cell Layer

---

## 🧠 Definition

The **runtime container** of all cellular data.

---

## 📦 Required Fields

```python
cell.id
cell.cell_type
cell.position

cell.node_state

cell.feature_params
cell.receptor_params
cell.behavior_params

cell.state  # HIR output
```

---

## ⚠️ Principles

```text
Cell MUST NOT:
✘ make decisions
✘ run behavior logic

Cell ONLY:
✔ stores state
✔ exposes data
```

---

# 🏭 6. CellFactory

---

## 🧠 Definition

Responsible for **instantiating cell instances**.

---

## 🔧 Responsibilities

```text
✔ generate unique ID
✔ initialize node_state
✔ sample parameters (feature/receptor/behavior)
✔ assign subtype
✔ set spatial position
```

---

## 🔮 Optional Extensions

```text
- snapshot export (debug)
- deterministic seed control
```

---

# 🧠 Key Design Principles

---

## 1. Separation of Concerns

```text
Node      → physics
HIR       → physiology constraint
Behavior  → decision
```

---

## 2. No Direct Cross-Layer Violations

```text
Behavior ❌ cannot bypass HIR
HIR ❌ cannot rewrite node directly
Node ❌ cannot trigger behavior
```

---

## 3. Deterministic Execution Order

Ensures reproducibility and debugging stability.

---

## 4. Unified State Commit

All updates must go through:

```text
update_state → commit
```

---

# 🚀 Next Step

After stabilizing InternalNet:

```text
→ InputBuilder (data shaping)
→ IntentBuilder (world interaction)
→ LabelCenter (state application)
```

---

# 🧩 Summary

```text
Node      = continuous biological variables
HIR       = state + fate regulator
Behavior  = conditional action generator
Update    = synchronization layer
Cell      = state container
```

---


