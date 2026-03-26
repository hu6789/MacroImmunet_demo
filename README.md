# MacroImmunet v0.3 — Multi-Cell Simulation Core
## Overview

MacroImmunet v0.3 introduces a multi-cell simulation framework for modeling immune-related cellular behavior in a structured and extensible way.

This version establishes a complete pipeline for:
 * multi-cell execution
 * cell-level heterogeneity
 * internal decision modeling
 * world interaction via an intent system

The system is designed to balance:
 * biological interpretability
 * modular extensibility
 * compute-aware scalability
## Core Architecture

The simulation follows a three-stage pipeline:
```
Scan → Decision → Apply
```
## Scan — Environment Sensing

Handled by:

 * ScanMaster

Responsibilities:

 * Read global state (LabelCenter)
 * Read local spatial signals (Space)
 * Construct receptor-level node_input
### Decision — Cell Internal Processing

Handled by:

 * InternalNet

 * (HIR embedded internally)

Responsibilities:

 * Process signals via node graph dynamics
 * Update internal state (node_state)
 * Produce:
  ○ behavior candidates
  ○ fate signals (via HIR)
### Apply — World Interaction

Handled by:

 * IntentBuilder
 * LabelCenter

Responsibilities:

 * Convert behaviors → intents
 * Queue updates
 * Apply all changes atomically per tick
## Simulation Loop
```python
for tick in range(ticks):

    for cell in cells:
        node_input = scan_master.scan(cell)
        result = internalnet.step(cell, node_input)

        intents = intent_builder.build(cell, result)
        all_intents.extend(intents)

    label_center.enqueue(all_intents)
    label_center.apply()

    space.diffuse()
```
## Cell System — Instance & Heterogeneity

Each cell is an independent entity:
```python
cell = Cell(config)
```
## Core Components
node_state → internal dynamic variables
feature_params → sampled parameters
capability → functional limits
meta → runtime state
## Heterogeneity (v0.3 Highlight)

Cells of the same type are not identical.

Parameter sampling:
```python
"stress_sensitivity": {
  "mean": 1.0,
  "std": 0.2
}
```
Handled by:
```
CellFactory → _apply_distribution()
```
## Subtypes

Discrete variation is supported:
```python
"subtypes": {
  "high_responder": {...},
  "low_responder": {...}
}
```
## Principle
```
Same cell type ≠ identical cells
```
## InternalNet — Cell Decision Engine

Pipeline:
```
node_input → node graph → HIR → behavior → state update
```
### Node System (Dynamics)
 * defined via JSON (node/defs, graph.json)
 * iterative update (bounded 0–1)
 * supports weighted, threshold, inverse rules
 * includes temporal smoothing (decay_tau)
### Input Integration

External signals are injected into node state:
```
node_state[k] = 0.9 * prev + v / (1 + v)
```
Supports nonlinear gating (e.g. IFN thresholding)

### HIR — Constraint & Fate Layer

HIR evaluates physiological feasibility.

Outputs:
```json
{
  "fate": "normal | stressed | dying",
  "scores": {...},
  "group_modifiers": {...},
  "blocks": {...}
}
```
Roles:

 * fate determination
 * constraint enforcement
 * behavior modulation
### Behavior System

Defined via JSON:

 * gate → drive → activation → output

Supports:

 * deterministic / probabilistic activation
 * HIR modulation
 * group-based scaling
### State Update

Behavior feeds back into internal state:
```json
"state_effects": {
  "ATP": -0.08,
  "stress": 0.05
}
```
## HIR — Homeostatic / Integrity Regulator

HIR is an embedded constraint system within InternalNet.

### Functional Roles
 * Fate Determination
continuous scoring → discrete state
 * Constraint Enforcement
block incompatible behaviors
suppress outputs under stress
 * Behavior Modulation
continuous scaling via group_modifiers
### Key Principle
```
HIR does not generate behavior — it only constrains it
```
### Important Property
```
HIR rules are global and consistent across cells
but outcomes depend on each cell's internal state
```
## Intent System — World Interaction Layer

Cells do not modify the world directly.

All interactions are expressed as:
```
Cell → Intent → LabelCenter.apply()
```
### Intent Pipeline
```
behavior → spec → filtered → bound → intent
```
### Stages
behavior → spec (semantic)
fate filter
binding (cell-specific parameters)
execution intent
### Special Rule
```python
if fate == "dying":
    return [{"type": "die"}]
```
### Design Principles
 * separation of semantics and execution
 * late binding of parameters
 * deterministic + batch execution
## World System — Environment & Spatial Interaction

Architecture:
```
LabelCenter → Space → ScanMaster
```
### LabelCenter (SSOT)
 * global state manager
 * intent queue + atomic apply
 * decay and saturation handling
### Space
 * spatial grid (x, y)
 * local field storage
 * cell positioning
 * diffusion (basic / evolving)
### ScanMaster
builds node_input
merges global + local signals
### World Flow
```
Intent → LabelCenter → Space → ScanMaster → Cell
```
### Key Design
```
Transactional world update (end-of-tick apply)
```
## Design Principles
1. Separation of Concerns
Scan ≠ Decision ≠ Apply
2. Intent-based Interaction
```
Cell → Intent → World
```
3. Deterministic Core + Variability
deterministic logic
stochastic parameter sampling
4. No Global Brain
per-cell decision
scalable architecture
## Current Capabilities
 * multi-cell simulation
 * cytokine secretion (IFN, IL6, TNF)
 * stress / damage modeling
 * heterogeneous cell population
 * spatial signal awareness
## Current Limitations
 * diffusion model is simplified
 * limited fate diversity
 * no event-driven optimization yet
 * no cell movement / interaction
## Example Run
```bath
python3 -m multi_cell_run_loop
```
## Project Structure
```
Internalnet/
intent/
world/
multi_cell_run_loop.py
```
## Summary

MacroImmunet v0.3 establishes a complete multi-cell simulation core with:

 * modular architecture
 * heterogeneous cell population
 * internal decision system
 * transactional world interaction
```
This version marks the transition from a single-cell model
to a scalable multi-cell simulation framework.
```
## AI Assistance

This project was developed with the assistance of AI tools (ChatGPT) for:

 * code structuring
 * documentation drafting
 * architectural discussions

All core design decisions, biological modeling logic, and system architecture were defined and validated by the author.
