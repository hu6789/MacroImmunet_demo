# MacroImmunet Demo

## A macro-scale immune system simulation framework

**MacroImmunet** is a research-oriented prototype exploring how a *transaction-consistent, ownership-aware Label Center* can serve as the single source of truth (SSOT) for spatial, agent-based immune simulations.

This demo focuses on *architecture clarity* rather than biological completeness, emphasizing **clear separation between sensing, decision, and world mutation**, and enabling higher-level immune logic to remain *pluggable, replaceable, and testable*.

> Status: architectural demo · not a validated biological model

---

## Core Design Ideas (TL;DR)

* **Three-stage pipeline**: Scan-time → Decision-time → Apply-time
* **LabelCenter = SSOT**: all world state lives here, all writes are transactional
* **Intent-only mutation**: no module mutates the world directly
* **Ownership & anti-double-counting** baked into the state layer
* **Decision engines are pluggable** (rule-based, network-based, ODE-based)

---

## Architecture 

```
┌───────────────────────────────┐
│        Apply-time             │
│   LabelCenter.apply(Intent)   │
│   - atomic commit per tick    │
│   - ownership / hysteresis    │
└───────────────▲───────────────┘
                │
        IntentBuilder
        - expand allowed fates
        - build atomic intents
                ▲
┌───────────────┴───────────────┐
│        Decision-time           │
│   CellMaster + Decision Core  │
│   - context assembly          │
│   - InternalNet / PerCell     │
│   - HIR (feasibility gate)    │
└───────────────▲───────────────┘
                │
┌───────────────┴───────────────┐
│         Scan-time              │
│        ScanMaster              │
│   - read-only world summary    │
│   - hotspot / contact detect  │
└───────────────────────────────┘
```
This inverted view emphasizes that world mutation is always the final step,
never mixed with sensing or decision logic.

---

## Key Modules
### 1. LabelCenter (State / Environment Layer)

Biological analogy: extracellular environment, antigen and cytokine distributions

Role: What exists right now?

Responsibilities:
* Maintain continuous spatial fields:
  * antigen density
  * cytokine concentrations
  * danger / stress signals

* Maintain discrete labels / super-particles:
  * aggregated antigen sources
  * active events and hotspots
* Handle state mechanics:
  * particle ↔ field conversion
  * decay (half-life), diffusion
  * merge / split with hysteresis
  * ownership rules to prevent double counting

This layer is intentionally passive: it never decides what should happen, only records what exists.

### 2. ScanMaster (Event Detection Layer)

Biological analogy: innate immune sensing, tissue surveillance

Role: Where should attention be paid?

Responsibilities:
* Periodically scan read-only summaries from LabelCenter
* Detect salient events:
  * antigen hotspots
  * rapid antigen increases
  * cell death or stress peaks
* Rank regions using configurable scoring functions:
  * density
  * temporal delta
  * novelty / recency

Emit structured NodeInput for downstream decision layers

ScanMaster answers "what is happening, and where" — without prescribing actions.

### 3. CellMaster (Cellular Decision Orchestrator)

Biological analogy: immune coordination, activation thresholds, clonal logic

Role: What should immune cells consider doing?

Responsibilities:
* Receive NodeInput from ScanMaster
* Organize cells by:
  * cell type
  * spatial region
  * genotype / internal state strata

Select and invoke an appropriate decision backend

Manage budgeting, batching, and throttling

Forward decision results to the world-application layer (via IntentBuilder)

CellMaster does not execute biology or mutate the world directly. It coordinates decision context.

### 4. Decision Core (InternalNet / PerCell)

Biological analogy: intracellular signaling pathways

Role: How do signals translate into cellular state changes?

Current status: lightweight architectural stub

Planned responsibilities:
 * Node–edge signaling propagation
 * Behavior activation with priorities

Adaptive thresholds or learning-based policies

This layer is the primary hook for future rule-based or learning-based extensions.

### 5. HIR — Homeostatic / Integrity Regulator

Biological analogy: cellular checkpoints and stress regulation

Role: Is a behavior physiologically feasible?

Responsibilities:
* Evaluate cell-level physiological summaries
* Allow, suppress, or bias behaviors
* Determine fate directions (e.g. divide, die, differentiate)

HIR does not generate world mutations; it only constrains what is biologically admissible.

### 6. IntentBuilder (World Realization Layer)

Biological analogy: execution of division, death, and effector outcomes

Role: How do allowed decisions concretely change the world?

Responsibilities:
* Translate allowed behaviors and fates into atomic Intents
* Determine quantity expansion and instantiation details
* Align all mutations with LabelCenter’s transactional semantics

IntentBuilder does not introduce new biological judgments; it ensures consistent realization of allowed outcomes.
---

## Immunological Mapping (Conceptual)

| Architecture Layer | Immunology Analogy                          |
| ------------------ | ------------------------------------------- |
| ScanMaster         | Antigen sensing / surveillance              |
| Decision Core      | Intracellular signaling & stress regulation |
| HIR                | Homeostasis & damage checkpoints            |
| IntentBuilder      | Effector realization                        |
| LabelCenter        | Tissue-scale physical reality               |

---


## Scope & Non-Goals

* ❌ Not a full immune system model

* ❌ Not parameter-validated biology

* ❌ Not optimized for performance

* ✅ Architecture exploration

* ✅ Consistency and causality clarity

* ✅ Long-term extensibility

---

## License & Usage

This repository is intended for research, prototyping, and architectural discussion.
Feel free to fork, experiment, or adapt the ideas with attribution.
Note: Some inline comments are bilingual due to development environment constraints during early prototyping.
Some refactoring and consistency checks were assisted by an AI-based coding assistant.
