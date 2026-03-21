# InternalNet v0.2 – Node & Rule Specification

This document defines the **core protocol** for InternalNet nodes in MacroImmunet v0.2.
All node libraries, HIR rules, and behaviors must follow this specification.

---

# 1. Node Schema

Standard structure for every node definition.

```json
{
  "node_id": "NFkB",
  "module": "inflammation",
  "category": "signal",
  "node_type": "transcription_factor",
  "state_class": "transient",

  "inputs": ["IKK"],

  "update_rule": "weighted_sum",

  "params": {
    "weights": [1.2]
  },

  "baseline": 0.1,
  "decay_tau": 3.0
}
```

---

# 2. Node Fields

| Field       | Description                                 |
| ----------- | ------------------------------------------- |
| node_id     | Unique node identifier                      |
| module      | Pathway module (e.g. antiviral, metabolism) |
| category    | Functional class of node                    |
| node_type   | Biological role                             |
| state_class | Determines accumulation behaviour           |
| inputs      | Upstream node list                          |
| update_rule | Mathematical update rule                    |
| params      | Parameters for the update rule              |
| baseline    | Default activation level                    |
| decay_tau   | Half‑life / decay constant                  |

---

# 3. Node Categories

Functional grouping used for rule tuning and HIR logic.

```
signal
sensor
viral
stress
metabolic
cytokine
apoptosis
structural
```

Example usage:

| Category   | Examples                  |
| ---------- | ------------------------- |
| signal     | NFkB, STAT1, MAPK         |
| sensor     | viral_sensor, DNA_sensor  |
| viral      | viral_RNA, viral_protein  |
| stress     | ROS, cell_stress          |
| metabolic  | ATP, translation_capacity |
| cytokine   | IFN_signal, TNF_signal    |
| apoptosis  | caspase, death_drive      |
| structural | membrane_integrity        |

---

# 4. Node State Classes

Defines whether a node accumulates over time.

```
transient
stock
resource
```

| Class     | Behavior                          |
| --------- | --------------------------------- |
| transient | recalculated each tick, no memory |
| stock     | accumulative variable with decay  |
| resource  | consumable pool (energy etc.)     |

Examples:

| Node      | Class     |
| --------- | --------- |
| NFkB      | transient |
| viral_RNA | stock     |
| ATP       | resource  |

---

# 5. Update Rules

Allowed mathematical update functions.

## weighted_sum

```
value = Σ(w_i * input_i)
```

---

## hill

```
value = x^n / (K^n + x^n)
```

---

## sigmoid

```
value = 1 / (1 + exp(-x))
```

---

## threshold

```
value = 1 if x > T else 0
```

---

# 6. Node Value Ranges

Signal nodes should generally stay within:

```
0 – 1
```

Stock/resource nodes may exceed this range depending on biological meaning.

---

# 7. Decay Rules

Nodes with decay follow exponential decay:

```
value *= exp(-dt / tau)
```

Where:

```
tau = decay_tau
```

---

# 8. Data Flow in InternalNet

```
cell_state + external_inputs
      ↓
Node Engine
      ↓
node_values
      ↓
HIR
      ↓
behavior_candidates
      ↓
State Update
      ↓
updated cell_state
```

---

# 9. Reserved Node Modules (Recommended)

```
antiviral
inflammation
stress_response
metabolism
apoptosis
```



