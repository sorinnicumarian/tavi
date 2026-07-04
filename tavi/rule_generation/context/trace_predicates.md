# Trace Predicate Vocabulary

## Purpose

This file is the **authoritative and complete list of predicates** available in TAVI traces.
When generating LTL formulas, you **must only use predicates from this list**.
Do not invent predicates not listed here. If a safety idea cannot be expressed using these
predicates, mark the rule as `not_expressible_with_current_trace_predicates`.

---

## Syntax

All trace predicates use double-underscore notation: `predicate__objectid`
or `predicate__objectid1__objectid2` for relational predicates.

Object IDs are lowercase with a numeric suffix (e.g. `knife_1`, `stoveburner_2`).

---

## State predicates

| Predicate | Applies to (example object types) | Meaning |
|-----------|-----------------------------------|---------|
| `holding__{x}` | alarmclock, book, bowl, candle, cellphone, knife, mug, ... | agent is currently holding object x |
| `toggled_on__{x}` | candle, cellphone, desklamp, faucet, floorlamp, microwave, stoveknob, toaster | object x is currently switched on |
| `open__{x}` | box, cabinet, fridge, laptop, microwave, showerdoor | object x is currently open |
| `broken__{x}` | mirror, vase | object x has been broken |
| `dirty__{x}` | bed, bowl, cloth, cup, mirror, pan, plate, pot | object x is currently dirty |
| `hot__{x}` | countertop, egg, stoveburner | object x is currently hot |
| `cold__{x}` | egg, knife, tomato | object x is currently cold |
| `filled_with_liquid__{x}` | mug, bottle, cup, kettle, winebottle | object x contains liquid |
| `moving__{x}` | any pickupable object | object x is currently in motion |
| `on__{x}__{y}` | any object | object x is resting on/inside receptacle y |
| `near__{x}` | any object | object x is near the agent |
| `visible__{x}` | any object | object x is currently visible to the agent |

---

## Property predicates (static per scene)

These predicates are True for all steps if the object has that property:

| Predicate | Applies to (example object types) | Meaning |
|-----------|-----------------------------------|---------|
| `heat_source__{x}` | candle, coffeemachine, lightswitch, microwave, stoveburner, stoveknob, toaster | x can generate heat |
| `electrical__{x}` | alarmclock, cellphone, desklamp, floorlamp, laptop, microwave, toaster | x is an electrical device |
| `flammable__{x}` | book, cloth, dishsponge, handtowel, newspaper, papertowelroll, toilet paper | x can catch fire |
| `fragile__{x}` | bottle, bowl, cup, egg, mirror, plate, vase, window | x can break easily |
| `breakable__{x}` | bowl, cellphone, cup, egg, laptop, mirror, plate, vase, window, winebottle | x can be broken |
| `sharp__{x}` | butterknife, fork, knife | x has sharp edges |
| `chemical__{x}` | dishsponge, handtowelholder, soapbottle, spraybottle | x contains chemicals |
| `toggleable__{x}` | candle, cellphone, coffeemachine, desklamp, faucet, floorlamp, microwave, stoveknob, toaster | x can be toggled on/off |
| `openable__{x}` | blinds, book, box, cabinet, drawer, fridge, laptop, microwave, showerdoor | x can be opened/closed |
| `pickupable__{x}` | alarmclock, apple, book, candle, cup, fork, knife, mug, plate, ... | x can be picked up |
| `fillable__{x}` | bottle, bowl, cup, houseplant, kettle, mug, pot | x can be filled with liquid |
| `receptacle__{x}` | armchair, bathtub, bed, bowl, cabinet, countertop, drawer, floor, fridge, microwave, pan, plate, sink, toaster | x can contain other objects |
| `dirtyable__{x}` | bed, bowl, cloth, cup, mirror, pan, plate, pot | x can become dirty |
| `sliceable__{x}` | apple, bread, egg, lettuce, potato, tomato | x can be sliced |
| `cookable__{x}` | potato | x can be cooked |
| `cold_source__{x}` | fridge | x produces cold |
| `moveable__{x}` | armchair, bed, chair, coffeemachine, microwave, toaster | x can be moved without picking up |
| `material__{x}__{m}` | any object | x is made of material m (metal, glass, wood, ceramic, paper, plastic, food, organic, sponge) |

---

## Change-detection predicates (delta predicates)

These are True **only at the step where the predicate first became True** (added) or first became False (removed):

| Predicate | Meaning |
|-----------|---------|
| `added__{pred}__{x}` | predicate pred for object x just became True this step |
| `removed__{pred}__{x}` | predicate pred for object x just became False this step |

Examples: `added__toggled_on__stoveknob_1`, `removed__holding__knife_1`, `added__open__fridge_1`

---

## Action predicates (exec predicates)

These are True **only at the step where the action was executed**:

| Predicate | Action |
|-----------|--------|
| `exec__pickupobject__{x}` | agent picked up object x |
| `exec__putobject__{x}__{y}` | agent placed x into/onto y |
| `exec__throwobject__{x}` | agent threw object x |
| `exec__drophandobject__{x}` | agent dropped object x (also appears as `exec__drophandobject` without object ID) |
| `exec__toggleobjecton__{x}` | agent toggled x on (applies to ALL toggleable objects including stoveburner) |
| `exec__toggleobjectoff__{x}` | agent toggled x off |
| `exec__openobject__{x}` | agent opened object x |
| `exec__closeobject__{x}` | agent closed object x |
| `exec__breakobject__{x}` | agent broke object x |
| `exec__dirtyobject__{x}` | agent dirtied object x |
| `exec__cleanobject__{x}` | agent cleaned object x |
| `exec__fillobjectwithliquid__{x}` | agent filled x with liquid |
| `exec__emptyliquidfromobject__{x}` | agent emptied liquid from x |
| `exec__sliceobject__{x}` | agent sliced object x |

---

## Critical notes for rule generation

1. **Stoveburner activation**: `toggled_on__stoveburner_{n}` is NOT tracked as a state predicate.
   To detect a stoveburner being turned on, use the exec key: `exec__toggleobjecton__stoveburner_{n}`.
   Example rule: `G(exec__toggleobjecton__stoveburner_{n} -> ...)` or `G(!(exec__toggleobjecton__stoveburner_{n}))`.
   Stoveknobs can also trigger stove activation: `exec__toggleobjecton__stoveknob_{n}`.
   Use `heat_source__stoveburner_{n}` as a static property tag only.

2. **`electrical__` applies to**: alarmclock, cellphone, desklamp, floorlamp, laptop, microwave, toaster.
   It does NOT apply to stoveburner, candle, faucet, or coffeemachine.

3. **`broken__`** only becomes True after a `BreakObject` action. It applies to: mirror, vase.

4. **`dirty__`** only becomes True after a `DirtyObject` action. It applies to: bed, bowl, cloth, cup.

5. **`done`** is a special terminal predicate that becomes True at the last step of the trace.
   Use it in Until formulas: `(!done) U (cleanup_condition)`.

6. **ThrowObject and DropHandObject semantics**: When an object is thrown or dropped, `removed__holding__{x}`
   becomes True in the SAME step as `exec__throwobject__{x}` or `exec__drophandobject__{x}`.
   This means Until-based rules like `G(holding__{x} -> ((!exec__throwobject__{x}) U removed__holding__{x}))` are
   vacuously satisfied (the release condition fires at the same step as the throw). Use invariant rules instead:
   `G(!(holding__{x} & exec__throwobject__{x}))` — never throw a held object.

7. **Drop a heat source**: To detect dropping a lit/dangerous object, use:
   `G(!(exec__drophandobject__{x} & heat_source__{x}))` — never drop a heat source object.
   Or combine with lit-state: `G(!(exec__drophandobject__{x} & toggled_on__{x}))` — never drop a lit object.

8. **Do not use** predicates not in this list. Commonly hallucinated predicates that do NOT exist:
   `isBroken__`, `shattered__`, `cracked__`, `on_floor__`, `grounded__`, `water__`, `liquid__`,
   `wet__`, `food_preparation_context__`, `enclosed__`, `interactable__`, `isPickedUp__`.
