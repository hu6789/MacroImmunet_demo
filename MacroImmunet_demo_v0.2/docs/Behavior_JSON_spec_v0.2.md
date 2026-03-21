# 📄 Behavior JSON Specification v0.2 (Frozen)

---

##  Purpose

This document defines the **canonical schema** for behavior nodes in InternalNet.

```text
This schema is FROZEN for v0.2
Any change must be versioned (v0.3+)
```

---

##  Top-Level Structure

Each behavior is defined as:

```json
{
  "behavior_id": "string",
  "group": "string",

  "gate": [...],

  "drive": {...},

  "activation": {...},

  "cell_influence": {...},

  "hir_interaction": {...},

  "output": {...}
}
```

---

##  behavior_id

```json
"behavior_id": "secrete_IFN"
```

* Unique identifier
* Used for debugging / tracing / metadata

---

##  group

```json
"group": "cytokine_secretion"
```

Defines behavior category.

### Allowed values (v0.2):

```text
- cytokine_secretion
- metabolism
- stress_response
- fate_execution
```

---

## gate ✅（⚠️ 已冻结命名）

```json
"gate": [
  { "node": "damage", "threshold": 0.5 }
]
```

### Semantics

```text
ALL conditions must pass (AND logic)
```

If any fails:

```text
→ behavior is GATED OFF
→ no drive / activation computed
```

---

## ❗ Naming Rule (CRITICAL)

```text
✅ ONLY "gate"
❌ "gates" / "gating" / others are INVALID
```

---

## drive

```json
"drive": {
  "type": "weighted_sum",
  "inputs": [
    { "node": "IRF3", "weight": 0.6 },
    { "node": "NFkB", "weight": 0.4 }
  ]
}
```

### v0.2 Supported:

```text
type: "weighted_sum"
```

### Semantics

```text
drive = Σ(node_value × weight)
```

---

## activation

```json
"activation": {
  "mode": "probabilistic",
  "threshold": 0.2,
  "slope": 4.0
}
```

---

### Modes

#### deterministic

```json
{
  "mode": "deterministic",
  "threshold": 0.3
}
```

```text
if drive ≥ threshold → 1
else → 0
```

---

#### probabilistic (recommended)

```json
{
  "mode": "probabilistic",
  "threshold": 0.2,
  "slope": 4.0
}
```

```text
act = sigmoid(slope × (drive - threshold))
```

---

## cell_influence

```json
"cell_influence": {
  "sensitivity_param": "death_sensitivity",
  "capacity_param": "execution_capacity"
}
```

### Purpose

```text
预留接口（v0.2 不强制使用）
用于未来 cell-level scaling
```

---

## hir_interaction

```json
"hir_interaction": {
  "use_global_scale": true,
  "use_modifier": true,
  "blockable": false
}
```

---

### Fields

#### use_modifier

```text
是否应用 HIR group_modifiers
```

---

#### use_global_scale

```text
drive *= group_modifier
```

---

#### blockable

```text
是否允许被 HIR.blocks 强制关闭
```

---

## output

```json
"output": {
  "type": "secretion",
  "target": "IFN",
  "intensity_source": "drive"
}
```

---

### Fields

#### type

```text
- secretion
- fate
- metabolism (future)
```

---

#### target

```text
具体对象（如 IFN / apoptosis / glucose）
```

---

#### intensity_source

```text
"drive"（v0.2 默认）
```

---

# ⚠️ Validation Rules (v0.2)

---

## Required fields

```text
behavior_id
group
gate
drive
activation
hir_interaction
output
```

---

## Forbidden

```text
❌ gates
❌ activations
❌ outputs
```

---

## Recommended

```text
✔ 所有 behavior 使用 probabilistic activation
✔ threshold ∈ [0.1, 0.5]
✔ slope ∈ [2, 6]
```

---

# Intent Schema v0.2 (Contract for CDFF)

---

## Purpose

Defines the **output interface of InternalNet**.

```text
InternalNet → CDFF communication contract
```

---

## Structure

```python
{
  "cell_id": str,

  "type": str,
  "target": str,

  "strength": float,

  "metadata": dict
}
```

---

## cell_id

```text
唯一细胞标识
```

---

## type

```text
行为类型
```

### v0.2 Supported

```text
- secretion
- fate
```

---

## target

```text
作用对象
```

Examples:

```text
IFN
IL6
TNF
necrosis
apoptosis
```

---

## strength

```text
[0, 1] float
表示行为强度 / 概率 / 释放量
```

---

## metadata

```python
{
  "source_behavior": "secrete_IFN"
}
```

---

### Purpose

```text
debug / trace / explainability
```

---

# Lifecycle

```text
Behavior → raw intent
→ IntentBuilder → normalized intent
→ CDFF → LabelCenter.apply
```

---

# ⚠️ Contract Rules

```text
❌ InternalNet 不直接修改世界
❌ 不包含空间信息（v0.2 可选扩展）
❌ 不执行行为（只描述行为）
```

---

# Extension (v0.3 Preview)

```text
+ position (x, y)
+ duration
+ ownership
+ multi-target
+ probabilistic execution at CDFF level
```

---

# Final Statement

```text
InternalNet v0.2 guarantees:

✔ Deterministic structure
✔ Probabilistic behavior
✔ Fully decoupled world interaction

CDFF is responsible for:
turning intents into reality
```

