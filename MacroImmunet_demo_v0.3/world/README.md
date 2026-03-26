World System — Environment \& Spatial Interaction

Overview



The World system manages all environment-related state and interactions.



It consists of three main components:



LabelCenter → Space → ScanMaster

Design Principles

1\. Single Source of Truth (SSOT)



All global state is stored in:



world/label/label\_center.py



Cells never modify the world directly.



2\. Transactional Updates



All changes are:



Intent → queue → apply (end of tick)



This ensures:



deterministic updates

no double counting

multi-cell consistency

3\. Separation of Global and Local Fields

global → LabelCenter

local → Space grid

&#x20;Components

1️⃣ LabelCenter

Role



Global field manager and write controller.



Responsibilities

store global fields

queue intents

apply updates atomically

handle decay and saturation

Example Fields

{

&#x20; "IFN": 0.0,

&#x20; "IL6": 0.0,

&#x20; "TNF": 0.0,

&#x20; "virus": 0.6,

&#x20; "damage": 0.0

}

Apply Pipeline

1\. process intents

2\. update global fields

3\. sync to spatial grid

4\. apply decay

5\. apply saturation

6\. clear queue

Field Metadata



Defined in:



field\_registry.py



Example:



"IFN": {"type": "substance", "decay": 0.1, "max": 5.0}

2️⃣ Space

Role



Handles spatial distribution of signals.



Structure

grid\[(x, y)] → {field: value}

Features

local field storage

cell positioning

diffusion (planned / partial)

Key Methods

place\_cell(cell\_id, pos)

get\_local\_field(pos, key)

add\_local\_field(pos, key, value)

Diffusion



Currently:



placeholder / simple averaging (in progress)



Future:



gradient-based diffusion

distance-aware spread

3️⃣ ScanMaster

Role



Provides environment input to cells.



Pipeline

LabelCenter + Space → node\_input

Example Output

{

&#x20; "IFN\_external": global IFN,

&#x20; "local\_IFN": local grid IFN,

&#x20; "IFN\_effective": weighted combination

}

Design Principle

Cells never read the world directly.

World Interaction Flow

Intent → LabelCenter → Space → ScanMaster → Cell

Current Limitations

diffusion model is simplified

no spatial heterogeneity initialization

no cell movement yet

no receptor-level spatial filtering

Future Directions

continuous diffusion model

spatial gradients

receptor-based sensing

cell movement / chemotaxis

spatial clustering

