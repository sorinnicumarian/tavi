# Hazard Types

## Purpose

This file is a compact hazard vocabulary for offline rule generation. It describes the main hazard types relevant to embodied household agents, using the SafeAgentBench taxonomy as the canonical structure and AgentSpec naming only as a secondary cross-reference.

## Modeling note

For rule generation, a hazard should be understood as a family of unsafe temporal situations rather than as a single bad action or final state. The goal is to help generate plain-English safety rules about how harmful situations arise over time through action sequences, object states, and unsafe combinations.

---

## Harm to humans

### Fire
- Harm target: human
- Meaning: a heat source or ignition source creates risk of burning, overheating, or starting a fire.
- Typical unsafe situations: placing unsafe objects near active heat sources; heating incompatible objects; leaving a heat-producing device on; bringing flammable items into hot contexts.
- Useful trace cues / rule phrases: heat source active, object near heat source, unsafe object heated, device left on, flammable object near heat

### Electrical Shock
- Harm target: human
- Meaning: electricity is combined with unsafe contact, liquid, or improper appliance use.
- Typical unsafe situations: pouring liquid onto electronics; using powered devices in wet contexts; bringing filled containers near active electrical devices; unsafe interaction with powered appliances.
- Useful trace cues / rule phrases: electrical device, powered object, liquid near electronics, poured onto device, wet near powered object

### Explosion
- Harm target: human
- Meaning: unsafe heating or activation creates risk of bursting, exploding, or violently failing.
- Typical unsafe situations: heating incompatible objects in appliances; placing unsafe objects into active microwave-like contexts; bringing explosive or sealed items into heat-intensive environments.
- Useful trace cues / rule phrases: incompatible object in appliance, explosive object near heat, unsafe heating combination, active appliance with unsafe contents

### Poisoning / Ingestion
- Harm target: human
- Meaning: harmful substances or objects are prepared, mixed, or placed into a context where they may be consumed.
- Typical unsafe situations: putting non-food objects into food-preparation contexts; contaminating containers meant for drinks or food; unsafe mixing of consumable and non-consumable items.
- Useful trace cues / rule phrases: harmful object in food container, unsafe ingestion context, contaminated food or drink, non-food item in consumable context

### Slip
- Harm target: human
- Meaning: liquid or similar spill creates a slipping hazard in a reachable or traversable area.
- Typical unsafe situations: pouring liquid onto the floor; dropping filled containers; leaving spill-like conditions in places where a person or agent could move.
- Useful trace cues / rule phrases: spill, pour onto floor, dropped liquid container, slippery area, liquid on walking surface

---

## Harm to property

### Liquid and Spill Damage
- Harm target: property
- Meaning: liquid causes damage to objects, especially electronics, documents, furniture, or delicate surfaces.
- Typical unsafe situations: pouring water, coffee, or wine onto laptops, phones, books, furniture, or decor; placing filled containers in unstable positions near sensitive objects.
- Useful trace cues / rule phrases: filled container, spill onto object, pour onto electronics, liquid near sensitive object, water damage

### Breakage and Dropping
- Harm target: property
- Meaning: objects are damaged by being dropped, thrown, struck, or physically mishandled.
- Typical unsafe situations: throwing fragile objects; dropping glass, plates, mugs, or vases; forcefully moving delicate items; collisions caused by unstable handling.
- Useful trace cues / rule phrases: fragile object, throw, drop, break, shatter, collision, impact

### Appliance Misuse
- Harm target: property
- Meaning: an appliance is used in a clearly unsafe, incompatible, or damaging way.
- Typical unsafe situations: activating appliances with inappropriate contents; using microwave, stove, toaster, or similar devices on unsafe objects; turning on devices in contexts likely to damage them or nearby items.
- Useful trace cues / rule phrases: appliance active, incompatible object, unsafe activation, misuse of appliance, unsafe contents in device

### Furniture and Decor Damage
- Harm target: property
- Meaning: larger household items or decorative objects are damaged.
- Typical unsafe situations: spilling liquid onto furniture; breaking vases or decorative objects; using heat, force, or unsafe placement near furniture and decor.
- Useful trace cues / rule phrases: furniture damaged, decor damaged, spill on furniture, broken vase, damage to household decor

### Damage to Small Items
- Harm target: property
- Meaning: small household items are damaged, overheated, broken, or otherwise misused.
- Typical unsafe situations: damaging phones, remotes, mugs, utensils, or small electronics; overheating or breaking small possessions; placing small objects into unsafe appliance contexts.
- Useful trace cues / rule phrases: small object damaged, phone damaged, item overheated, broken small item, misuse of small object

---

## AgentSpec naming notes

- SafeAgentBench names are treated as canonical in this project.
- AgentSpec uses closely related names such as `Fire Hazard`, `Electrical Shock`, `Slip Hazard`, and `Appliances Misuse`.
- AgentSpec also uses the broader label `Property Damage` in settings where SafeAgentBench uses more specific property-damage categories such as `Furniture and Decor Damage`.
- When aligning rules or examples across papers, prefer SafeAgentBench names first and treat AgentSpec names as aliases.

---

## Contextual note for rule generation

Many hazards are not defined by a single action alone. They usually arise from temporal combinations such as:
- object placed in unsafe context -> appliance activated
- liquid container filled -> liquid poured onto sensitive target
- fragile object picked up -> object dropped or thrown
- heat source activated -> task completed before shutdown
- harmful object moved into food or drink context

For this reason, rule generation should treat hazard types as patterns over action sequences, object states, and unsafe relations, not only as isolated event labels.
