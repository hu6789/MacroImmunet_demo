# MacroImmunet Demo

## A macro-scale immune system simulation framework

**MacroImmunet** is a modular, event-driven *research demo* for simulating immune responses at the **tissue / organ scale**.
Rather than reproducing full single-cell biophysics, it explores **how immune behavior emerges from structured coordination layers** acting over spatial fields.

At its core, MacroImmunet treats the immune system as a **control system**:
fields are sensed, events are prioritized, decisions are coordinated, and actions are selectively executed.

This demo is **not** a wet-lab–faithful simulator. Instead, it is designed to provide:

* a **clear architectural separation** between sensing, decision, and execution;
* a **scalable control abstraction** for heterogeneous immune populations;
* a **plugin-ready sandbox** for future high-fidelity cell models, signaling networks, and learning modules.

If you are interested in *how immune dynamics can be organized, not just simulated*, this repository is for you.

---

## Conceptual Overview

MacroImmunet models immunity as a **multi-layer control pipeline** operating over a spatial grid:

```
Field / Label Layer   (what exists)
↓
Scan Master           (what is happening?)
↓
Cell Master           (what should immune cells do?)
↓
Per-Cell Engine       (how exactly is it executed?)
```

Each layer has a **single responsibility** and trades biological detail for:

* computational tractability,
* explicit decision boundaries,
* and replaceability via plugins.

---

---

## Core Modules Explained

### 1. Label Center (State / Field Layer)

**Biological analogy**: extracellular environment, antigen and cytokine distributions
**Role**: *What exists right now?*

Responsibilities:

* Maintain **continuous spatial fields**

  * antigen density
  * cytokine concentrations
  * danger / stress signals
* Maintain **discrete labels / super-particles**

  * aggregated antigen sources
  * events and hotspots
* Handle state mechanics:

  * particle ↔ field conversion
  * decay (half-life), diffusion
  * merge / split with hysteresis
  * ownership rules to prevent double counting

This layer is intentionally **passive**:
it never decides *what should happen*, only records *what exists*.

---

### 2. Scan Master (Event Detection Layer)

**Biological analogy**: innate immune sensing, tissue surveillance
**Role**: *Where should attention be paid?*

Responsibilities:

* Periodically scan **grid summaries** from the Label Center
* Detect salient events:

  * antigen hotspots
  * rapid antigen increases
  * death or stress spikes
* Rank regions using configurable **score functions**

  * density
  * temporal delta
  * recency / novelty
* Emit **node inputs** for downstream decision layers

Scan Master answers *"what is happening, and where"* —
without prescribing actions.

---

### 3. Cell Master (Cellular Decision Layer)

**Biological analogy**: immune coordination, activation thresholds, clonal logic
**Role**: *What should immune cells do?*

Responsibilities:

* Receive node inputs from Scan Master
* Batch-handle immune cells by:

  * cell type
  * spatial region
  * genotype / internal state strata
* Apply decision logic:

  * gene judges / gating rules
  * InternalNet signaling evaluation
* Convert activations into **structured intents**:

  * kill / migrate / proliferate
  * cytokine secretion
  * differentiation or memory flags

Cell Master **does not execute biology**.
It produces *intent packages* that can later be executed at different fidelities.

---

### 4. InternalNet (Immune Signaling Network)

**Biological analogy**: intracellular signaling pathways
**Role**: *How does signal become behavior?*

Current status: **lightweight stub**

Planned responsibilities:

* Node–edge signaling propagation
* Behavior activation with priorities
* Adaptive thresholds or learned policies

This module is the **primary hook** for future ML-, rule-, or graph-based plugins.

---

### 5. Per-Cell Engine (High-Fidelity Executor)

**Biological analogy**: individual immune cell dynamics
**Role**: *How exactly is a decision executed?*

Current status: **placeholder interface**

Design intent:

* Spawned **only when needed**, under explicit budget control
* Run detailed ODE / compartment / stochastic models
* Write back **summarized effects** to the Label Center

This allows precision where it matters, without sacrificing global scalability.

---

## Execution Model

* Simulation advances in discrete **ticks**
* All state writes are **queued** and applied **transactionally** at tick end
* Per-cell execution temporarily overrides bulk updates
* Cooldown and hysteresis prevent oscillatory behavior

This mirrors immune stability under homeostasis versus emergency escalation.

---

## Testing Philosophy

Tests are organized around **architectural milestones**, not biological claims:

* `step7_x`: interface contracts, data flow correctness, replayability
* later stages: integration, stress tests, behavior consistency

Passing tests means that **layers agree on contracts** —
not that immunity has been fully solved.

---

## Future Plugin Directions

Planned and anticipated extensions include:

* Learning-based InternalNet (RL / GNN / hybrid)
* Alternative Scan Masters (virus-specific, tumor-specific)
* Multi-organ or multi-tissue coordination
* Antigen lifecycle and "skill" abstractions
* Visualization, logging, and replay tools

The system is designed to evolve **by replacement, not by rewrite**.

---

## Who Is This For?

This demo is primarily aimed at:

* **Computational immunology and simulation researchers**
* **Multi-agent and control-system modelers**
* **Systems biologists who care about architecture first**

Readers from immunology or biology backgrounds should be able to follow the concepts,
even without deep infrastructure experience.

If you believe that *immune systems are control systems*, you are in the right place.



Note: Some inline comments are bilingual due to development environment constraints during early prototyping.
Some refactoring and consistency checks were assisted by an AI-based coding assistant.
