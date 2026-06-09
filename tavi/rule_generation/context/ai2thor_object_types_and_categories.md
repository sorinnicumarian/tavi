# AI2THOR object types and categories

## Purpose

This file defines the compact object-type grounding layer used by rule generation and LTL-template generation.

It answers only this question:

> When a rule mentions a semantic object category, which AI2-THOR object types can ground that category?

This file should not duplicate:
- the full AI2-THOR object-state vocabulary;
- the full action vocabulary;
- the hazard taxonomy;
- the LTL atom syntax guide;
- long prompt instructions.

Those belong in the other context files.

---

## Core rule

Rules should use semantic category predicates, not raw object-type predicates.

Good:

```text
heat_source__{h}
flammable__{x}
fragile__{x}
electrical__{x}
sharp__{x}
chemical__{x}
```

Bad:

```text
microwave__{x}
stoveburner__{x}
is_mug__{x}
unsafe_object__{x}
dangerous__{x}
incompatible__{x}
```

Concrete AI2-THOR object types are used only later for grounding variables over the trace.

---

## Semantic categories

### heat_source

Predicate: heat_source__{x}


Current object-type grounding candidates:

```text
StoveBurner
StoveKnob
Microwave
Toaster
CoffeeMachine
Candle
LightSwitch
DeskLamp
FloorLamp
```

Note:
Some of these are strict heat sources, while others are currently grouped as activation or ignition-related objects by the trace processor. If this becomes too broad later, split the category in code first, then update this file.

---

### flammable

Predicate: flammable__{x}

Current object-type grounding candidates:

```text
PaperTowelRoll
Book
Cloth
DishSponge
Newspaper
TissueBox
Towel
HandTowel
ToiletPaper
```

---

### fragile

Predicate: fragile__{x}

Current object-type grounding candidates:

```text
Vase
Egg
WineBottle
Plate
Cup
Bowl
Glass
Bottle
Jar
Mirror
Window
```

Related atoms:

```text
breakable__{x}
broken__{x}
added__broken__{x}
```

---

### sharp

Predicate: sharp__{x}

Current object-type grounding candidates:

```text
Knife
ButterKnife
Fork
Scissors
Shard
```

Related atoms:

```text
holding__{x}
added__holding__{x}
removed__holding__{x}
exec__SliceObject__{x}
```

---

### electrical

Predicate: electrical__{x}

Current object-type grounding candidates:

```text
Laptop
Television
Microwave
Toaster
CellPhone
AlarmClock
DeskLamp
FloorLamp
```

Related atoms:

```text
toggleable__{x}
toggled_on__{x}
added__toggled_on__{x}
removed__toggled_on__{x}
```

---

### chemical

Predicate: chemical__{x}

Current object-type grounding candidates:

```text
SprayBottle
SoapBottle
DishSponge
HandTowelHolder
BottleOfBleach
```

Use this category for poisoning, contamination, or unsafe cleaning-material rules.

Do not invent:

```text
poisonous__{x}
toxic__{x}
cleaning_agent__{x}
```

unless the trace processor later emits those predicates.

---

## Liquid containers

Use capability/state atoms instead of object-type predicates.

Relevant atoms:

```text
fillable__{x}
filled_with_liquid__{x}__water
filled_with_liquid__{x}__coffee
filled_with_liquid__{x}__wine
```

Example object types that are often fillable:

```text
Mug
Cup
Bowl
Bottle
WineBottle
Pot
Pan
Kettle
WateringCan
HousePlant
```

Do not create liquid variables such as:

```text
flammable__{wine}
liquid__{l}
```

Use the container state instead:

```text
filled_with_liquid__{c}__wine
```