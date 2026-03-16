# MacroImmunet_demo_v0.1

## Overview

This repository contains a minimal runnable demonstration of the MacroImmunet architecture.

The demo verifies the integration of the core runtime pipeline:

World → ScanMaster → CellMaster → Behavior → IntentBuilder → LabelCenter

The goal is not to simulate full biological processes yet, but to confirm that the core architectural components interact correctly and produce interpretable execution traces.

## Architecture Overview

The demo implements the minimal MacroImmunet runtime pipeline.
World
↓
ScanMaster
↓
CellMaster
↓
IntentBuilder
↓
LabelCenter

Each stage prints trace outputs to allow developers to observe signal propagation and decision formation.

---

## Pipeline Layers

### World

The World represents the minimal simulation environment.

Example initialization:

```

[World] Initial cells:
{'id': 'cell_1', 'type': 'epithelial', 'state': 'healthy', 'health': 100}
{'id': 'cell_2', 'type': 'virus', 'state': 'free', 'replication_level': 1}

```

Responsibilities:

- store cell instances
- provide environmental context
- act as the data source for ScanMaster

---

### ScanMaster

ScanMaster performs environmental perception.

Responsibilities:

- scan the environment
- detect interaction signals
- generate structured event outputs

Example scan output:

```

{
"signals": {"pMHC_candidate": 1.0},
"events": [
{
"signal": "pMHC_candidate",
"source": "cell_2",
"target": "cell_1",
"strength": 1.0
}
]
}

```

---

### CellMaster

CellMaster coordinates per-cell decision processing.

Responsibilities:

- receive ScanMaster outputs
- assemble node inputs
- execute decision logic
- produce abstract behaviors

Example behavior output:

```

attack
secrete
divide
die
differentiate

```

Behaviors are intermediate decisions and not yet executable world actions.

---

### IntentBuilder

IntentBuilder converts behaviors into atomic intents.

Example intent structure:

```

{
"type": "attack",
"source": "cell_2",
"target": null,
"payload": {},
"meta": {
"cell_id": "cell_2",
"engine": "MiniNet"
}
}

```

---

### LabelCenter

LabelCenter is the single source of truth (SSOT) for world state updates.

Responsibilities:

- receive intents
- queue state updates
- apply changes at tick boundaries

The demo version only verifies pipeline compatibility.

---

## Running the Demo

Run the demo:

```

python3 -m demo.demo_trace_run

```

Run tests:

```

python3 -m pytest cdff/test -vv

```
---

## Execution Trace

The demo prints the full runtime pipeline:

World initialization  
↓  
ScanMaster scanning  
↓  
CellMaster processing  
↓  
IntentBuilder conversion  
↓  
LabelCenter apply  

---

## Purpose

The demo verifies that:

- ScanMaster → CellMaster integration works
- Behavior → Intent conversion works
- LabelCenter accepts intents
- the pipeline produces interpretable traces

This provides a stable foundation for future MacroImmunet development.

---

## Future Extensions

Planned future demos include:

- multi-cell simulations
- infection dynamics
- HIR integration
- cytokine signaling
- spatial simulation environments
