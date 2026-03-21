# MacroImmunet Demo v0.2

## Overview

**MacroImmunet v0.2** establishes the core execution pipeline of a multi-cell immune simulation system.

This version focuses on **architecture validation**, ensuring that the full decision loop—from environmental sensing to world-state updates—is coherent, reproducible, and extensible.

---

## Core Pipeline

Each simulation tick follows a strict three-stage pipeline:

```
Scan-time → Decision-time → Apply-time
```

### 1. Scan-time

* Environment is summarized (future: via `ScanMaster`)
* Cells receive contextual input (currently simplified)

### 2. Decision-time

* `CellMaster` invokes `InternalNet`
* InternalNet performs:

  * Signal processing
  * Physiological state update
  * Behavior generation
* `HIR (Homeostatic / Integrity Regulator)` filters behaviors based on physiological feasibility

### 3. Apply-time

* Behaviors are translated into **atomic Intents**
* All Intents are submitted to `LabelCenter`
* `LabelCenter.apply()` performs **transactional world updates at tick end**

---

## Key Components

### CellInstance

* Lightweight data container
* Stores:

  * `node_state` (dynamic intracellular state)
  * `base_values` (cell-specific variability)
  * metadata (state, age, tags)

### InternalNet

* Core intracellular decision engine
* Produces:

  * `behavior_candidates`
  * updated `node_state`

### HIR (Homeostatic / Integrity Regulator)

* Enforces physiological constraints
* Filters or modifies behaviors based on:

  * stress
  * damage
  * metabolic state (e.g., ATP)

> ⚠️ In v0.2, HIR acts primarily as a soft regulator. Strict gating will be introduced in future versions.

### IntentBuilder

* Converts allowed behaviors into atomic **Intents**
* Handles:

  * behavior expansion
  * parameter mapping
  * ownership consistency

### LabelCenter (SSOT)

* Single Source of Truth for world state
* Handles:

  * field updates (e.g., IFN)
  * state transitions
* All updates are:

  * queued
  * applied atomically at tick end

---

## Running the Demo

```bash
python3 -m cdff.run.run_v0_2_demo
```

### Demo Includes

* Multiple cell instances
* InternalNet execution per cell
* Behavior → Intent conversion
* Field accumulation (e.g., IFN secretion)
* Transactional application via LabelCenter

---

## Example Output (Simplified)

```
[CellMaster] Running InternalNet for cell_0
→ behaviors: autophagy, necrosis, secrete_IFN
→ intents: state_update, fate, secretion

[LabelCenter] Applying intents...

[Field]
IFN: increasing over time
```

---

## ⚠️ Current Limitations (v0.2 Scope)

This version prioritizes **pipeline correctness over biological realism**.

### Not yet implemented:

* ❌ Substance lifecycle (decay / diffusion / half-life)
* ❌ Temporal dynamics (state accumulation / decay across ticks)
* ❌ Strict physiological gating (e.g., ATP-constrained behavior blocking)
* ❌ Effective use of cell-specific variability (`base_values`)
* ❌ Multi-cell-type specialization
* ❌ Spatial modeling (2D environment, ScanMaster)

---

## 🧾 Notes

MacroImmunet is designed as a **modular, extensible simulation framework**, where:

* Decision logic is **cell-intrinsic**
* World state is **centrally managed**
* All interactions occur via **Intents**



