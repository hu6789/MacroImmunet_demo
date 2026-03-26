Intent System — World Interaction Layer

Overview



The Intent system defines how cells interact with the world.



Instead of directly modifying the environment, all actions are expressed as:



Cell → Intent → LabelCenter.apply()



This ensures:



consistency

atomic updates

conflict-free multi-cell execution

Intent Pipeline



The transformation from internal behavior to world action follows:



behavior → intent spec → filtered spec → bound intent

1️⃣ Behavior Interpretation



File:



intent/behavior\_interpreter.py

Role



Converts behavior outputs into intent specifications (specs).



Example

interpret\_behavior(...)

{

&#x20; "intent\_type": "add\_field",

&#x20; "target": "IFN",

&#x20; "base": drive,

&#x20; "activation": activation

}

Key Property

Spec is cell-independent and purely semantic

2️⃣ Fate Filtering



File:



intent/fate\_filter.py

Role



Filters intent specs based on cell fate.



Example

dying → only allow apoptosis-related behaviors

Note



This is a secondary safeguard on top of HIR.



3️⃣ Intent Binding



File:



intent/intent\_binding.py

Role



Transforms specs into final executable intents.



This step injects:



cell-specific parameters

scaling factors

output normalization

Example

value = (

&#x20;   base

&#x20;   \* activation

&#x20;   \* capacity

&#x20;   \* sensitivity

&#x20;   \* scale

)

Additional Scaling

GROUP\_SCALE = {

&#x20; "cytokine\_secretion": 10.0,

&#x20; ...

}

Output

{

&#x20; "type": "add\_field",

&#x20; "cell\_id": "...",

&#x20; "target": "IFN",

&#x20; "value": 0.42

}

4️⃣ Intent Builder



File:



intent/intent\_builder.py

Role



Coordinates the full pipeline:



behavior → spec

fate filter

binding → intent

Special Rule: Fate Priority

if fate == "dying":

&#x20;   return \[{"type": "die"}]

Design Principle

fate overrides behavior

Design Principles

1\. Intent as the Only Action Language



Cells do not modify the world directly.



2\. Separation of Semantics and Execution

spec → meaning

intent → execution

3\. Late Binding



Cell-specific parameters are only applied at the final stage.



4\. Deterministic + Scalable



Intent system enables:



batching

atomic apply

replay / debugging

Notes

Fate filtering is currently simple (expandable)

Group scaling is manually defined (future: adaptive)

Intent types are currently limited (extensible)

