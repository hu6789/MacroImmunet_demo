Cell System — Instance \& Heterogeneity

Overview



The Cell system represents individual entities in the simulation.



Each cell instance contains:



internal state (node\_state)

functional capabilities

sampled parameters (heterogeneity)

Cell Structure



Defined in:



Internalnet/cell/cell\_instance.py

Core Fields

cell.node\_state        # dynamic internal variables

cell.feature\_params    # sampled parameters

cell.capability        # functional limits

cell.meta              # runtime state

Cell Configuration



Defined via JSON:



{

&#x20; "cell\_type": "test\_cell",

&#x20; "init\_node\_state": {...},

&#x20; "feature\_params": {...},

&#x20; "subtypes": {...}

}

Heterogeneity (Key Feature)



Cell variability is introduced through parameter sampling:



CellFactory.\_apply\_distribution()

Supported Distributions

normal

lognormal

fixed value

Example

"stress\_sensitivity": {

&#x20; "mean": 1.0,

&#x20; "std": 0.2

}

Subtypes



Optional subtype sampling introduces discrete variation:



"subtypes": {

&#x20; "high\_responder": {...},

&#x20; "low\_responder": {...}

}

Behavior

one subtype selected per cell

overrides selected parameters

Capability vs Parameters

Field	Role

capability	hard functional limits

feature\_params	continuous variation

Lifecycle



Cells are created via:



CellFactory.create(cell\_type)

Initialization Steps

load config

create instance

sample parameters

assign subtype (optional)

Design Principles

1\. Instance-Level Variability

Same cell type ≠ identical cells

2\. Separation of Structure and Parameters

structure → node graph

parameters → cell instance

3\. Lightweight Representation



Cells are minimal containers:



no embedded logic

no direct world interaction

Notes

parameter schema is evolving

subtype system is extensible

no lineage / division yet (planned)

