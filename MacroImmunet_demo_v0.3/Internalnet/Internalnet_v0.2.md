# 📄 README.md — InternalNet v0.2

---

## What is InternalNet

**InternalNet** is the intracellular decision engine of MacroImmunet.

It transforms:

```text
cell state → behaviors → atomic intents
```

---

### Core Philosophy

```text
✔ Cells do not act directly
✔ Cells decide what they want to do
✔ The world executes those decisions
```

---

## Role in MacroImmunet

InternalNet sits at **Decision-time** in the system pipeline:

```text
ScanMaster (environment sensing)
        ↓
CellMaster (context organization)
        ↓
InternalNet (this module)
        ↓
IntentBuilder
        ↓
LabelCenter (world state, Apply-time)
```

---

## Internal Pipeline

```text
Node State (intracellular signals)
        ↓
HIR (feasibility & physiological regulation)
        ↓
Behavior System (drive + activation)
        ↓
IntentBuilder (normalization)
        ↓
INTENTS (final output)
```

---

## Output Interface (CRITICAL)

InternalNet does **NOT** modify the world.

It outputs:

```python
intents = [
    {
        "cell_id": "cell_1",
        "type": "secretion",
        "target": "IFN",
        "strength": 0.67,
        "metadata": {
            "source_behavior": "secrete_IFN"
        }
    }
]
```

---

## Integration with CDFF

### Contract

```text
InternalNet → CDFF
```

---

### InternalNet Responsibilities

```text
✔ Compute intracellular dynamics
✔ Apply HIR constraints
✔ Generate behaviors
✔ Output atomic intents
```

---

### CDFF Responsibilities

```text
Consume intents
Convert intents → world state changes
Call LabelCenter.apply (atomic commit)
```

---

### ❗ Important Rules

```text
❌ InternalNet cannot:
  - modify world state
  - access spatial grid
  - execute behaviors

❌ CDFF cannot:
  - override HIR infeasibility
```

---

## HIR (Homeostatic / Integrity Regulator)

HIR is embedded inside InternalNet.

### Responsibilities

```text
✔ Decide physiological feasibility
✔ Apply group-level modifiers
✔ Block dangerous behaviors
✔ Trigger fate states (dying / stressed / etc.)
```

---

### Example Output

```python
{
  "fate": "normal",
  "group_modifiers": {
    "cytokine_secretion": 0.97,
    "metabolism": 0.21,
    "stress_response": 0.2,
    "fate_execution": 1.0
  },
  "blocks": {}
}
```

---

## Behavior System

Each behavior is defined via **Behavior JSON Spec v0.2**.

### Core Mechanics

```text
1. Gate check (on/off)
2. Drive computation
3. Activation mapping (probabilistic)
4. HIR modulation
5. Output mapping → intent
```

---

### Example

```text
secrete_IFN:
  drive = 0.679
  → activation = 0.672
```

---

## How to Run

From project root:

```bash
python3 -m Internalnet.run_simulation
```

---

### Expected Output

```text
=== HIR OUTPUT ===
{...}

=== BEHAVIOR EXECUTION ===
secrete_IFN: drive=0.679 → act=0.672
...

=== BEHAVIOR OUTPUT ===
{...}
```

---

## Project Structure (simplified)

```text
Internalnet/
├── run_simulation.py
├── behavior/
├── hir/
├── intent_builder/
├── config/
└── utils/
```

---

## Versioned Specifications

* Behavior Schema → `Behavior JSON Spec v0.2`
* Intent Interface → `Intent Schema v0.2`

```text
⚠️ These are frozen contracts for v0.2
```

---

## Extension Roadmap (v0.3)

```text
+ Multi-cell integration (ScanMaster input)
+ Spatial awareness (via CDFF only)
+ More behavior types (migration, interaction)
+ Rich intent metadata (duration, ownership)
```

---

## Design Principle Summary

```text
InternalNet = "brain"
CDFF = "body"
LabelCenter = "reality"
```

---

## Final Statement

```text
InternalNet v0.2 provides:

✔ Deterministic structure
✔ Probabilistic behavior
✔ Clean system boundary

It is ready to be plugged into CDFF.
```


