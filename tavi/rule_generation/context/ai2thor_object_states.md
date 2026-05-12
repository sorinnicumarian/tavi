# AI2-THOR Object States

## Purpose

This file is a compact state vocabulary for offline rule generation. It describes the main object states and object-state relations that matter for temporal safety rule synthesis in AI2-THOR: what each state means, why it matters for safety reasoning, and how it can appear in a trace.

## Modeling note

For rule generation, object states should be understood as symbolic conditions that may hold over time, such as `microwave is open`, `mug is filled with water`, `knife is picked up`, or `plate is inside sink`. The goal is not to list all simulator metadata, but only the state concepts most useful for generating plain-English temporal rules.

---

## Visibility and accessibility states

### visible
- Meaning: the object is currently visible to the agent.
- Safety relevance: visibility often enables later interaction; many hazardous sequences begin once a risky object or device is noticed.
- Useful trace predicates / phrases: visible, seen, in view, observed, near

### interactable
- Meaning: the object is currently in a state where the agent can directly interact with it.
- Safety relevance: more important than visibility alone, since many risky actions only become possible when an object is interactable.
- Useful trace predicates / phrases: interactable, reachable for interaction, accessible

---

## Possession and movement states

### pickupable
- Meaning: the object is of a kind that can be picked up and carried by the agent.
- Safety relevance: pickupable objects can be transported into hazardous contexts such as heat sources, sinks, fragile areas, or electrical devices.
- Useful trace predicates / phrases: pickupable, carriable, can be picked up, holding

### isPickedUp
- Meaning: the object is currently being held by the agent.
- Safety relevance: being held is a key state in many temporal hazard chains, because it allows transport, pouring, throwing, or unsafe placement.
- Useful trace predicates / phrases: held, being carried, in hand, picked up

### moveable
- Meaning: the object can be moved through force or physical interaction even if it is not picked up.
- Safety relevance: moveable objects can still be displaced into unsafe positions by pushing, pulling, or collisions.
- Useful trace predicates / phrases: moveable, can be moved, displaceable

### isMoving
- Meaning: the object is currently in motion.
- Safety relevance: movement can indicate unstable or dangerous situations such as falling, rolling, or recently disturbed fragile objects.
- Useful trace predicates / phrases: moving, in motion, displaced

---

## Containment and placement states

### receptacle
- Meaning: the object can contain or support other objects.
- Safety relevance: receptacles are central to many safety rules because dangerous states often depend on what is placed in, on, or near them.
- Useful trace predicates / phrases: receptacle, container, support surface, can contain objects

### receptacleObjectIds
- Meaning: the object currently contains or supports other objects.
- Safety relevance: lets rules talk about unsafe combinations such as an object inside a microwave, on a stove, in a sink, or near another risky object.
- Useful trace predicates / phrases: contains, holds, has inside, has on top, on, inside, in (the last three refer to the first argument of the state)

### parentReceptacles
- Meaning: the object is currently inside or on another receptacle.
- Safety relevance: this is one of the most useful relations for temporal rules because containment often determines whether a later activation becomes dangerous.
- Useful trace predicates / phrases: inside, in, on, placed in, placed on, contained by, on, inside, in (the last three refer to the second argument of the state. If multiple objects, they are separated by the "|" symbol).

---

## Activation states

### openable
- Meaning: the object can be opened and closed.
- Safety relevance: openable objects often gate access to contents and enable later risky interactions.
- Useful trace predicates / phrases: openable, can be opened,

### isOpen
- Meaning: the object is currently open.
- Safety relevance: open objects expose contents, allow insertion or removal, and often participate in action sequences such as open -> place -> close -> activate.
- Useful trace predicates / phrases: open, opened, unsealed

### toggleable
- Meaning: the object can be switched on and off.
- Safety relevance: toggleable devices often become active hazard sources when turned on.
- Useful trace predicates / phrases: toggleable, can be turned on, can be switched

### isToggled
- Meaning: the object is currently on or active.
- Safety relevance: one of the most important states for safety rules because an active device may produce heat, power, water flow, or another ongoing effect.
- Useful trace predicates / phrases: on, active, running, switched on, enabled, toggled_on

---

## Condition-change states

### breakable
- Meaning: the object can enter a broken state.
- Safety relevance: breakable objects are relevant to property-damage rules and to secondary hazards caused by damaged objects.
- Useful trace predicates / phrases: breakable, fragile enough to break, can be damaged

### isBroken
- Meaning: the object is currently broken.
- Safety relevance: indicates property damage and can also signal unsafe aftermath conditions.
- Useful trace predicates / phrases: broken, damaged, shattered, cracked

### sliceable
- Meaning: the object can be sliced into another form.
- Safety relevance: relevant for preparation-related rules and for sequencing rules involving knives or sharp tools.
- Useful trace predicates / phrases: sliceable, can be cut

### isSliced
- Meaning: the object is currently in a sliced form.
- Safety relevance: records that a cutting action has already occurred; useful in temporal sequencing and task-completion rules.
- Useful trace predicates / phrases: sliced, cut, chopped

### cookable
- Meaning: the object can become cooked.
- Safety relevance: cookable objects are central to rules involving heat, appliances, timing, and shutdown obligations.
- Useful trace predicates / phrases: cookable, can be heated, can be cooked

### isCooked
- Meaning: the object is currently cooked.
- Safety relevance: shows that heating or cooking has already taken effect; useful for stopping conditions and for detecting unsafe over-processing sequences.
- Useful trace predicates / phrases: cooked, heated, prepared

### dirtyable
- Meaning: the object can become dirty or clean.
- Safety relevance: useful for rules involving cleaning tasks, sink usage, or unsafe mixing of dirty and clean objects.
- Useful trace predicates / phrases: dirtyable, can become dirty

### isDirty
- Meaning: the object is currently dirty.
- Safety relevance: relevant for cleaning-task constraints and for rules about when washing-related actions are appropriate.
- Useful trace predicates / phrases: dirty, unclean, soiled

### canBeUsedUp
- Meaning: the object can be consumed or depleted through use.
- Safety relevance: useful for reasoning about finite-use resources and completion states.
- Useful trace predicates / phrases: consumable, depletable, can be used up

### isUsedUp
- Meaning: the object has already been used up or depleted.
- Safety relevance: can mark irreversible resource consumption and affect whether later actions remain appropriate.
- Useful trace predicates / phrases: used up, depleted, exhausted

---

## Temperature and liquid states

### ObjectTemperature
- Meaning: the object has an abstract temperature state such as hot, cold, or room temperature.
- Safety relevance: temperature is one of the most important safety-relevant states because heat and cold strongly affect whether placement or contact becomes dangerous.
- Useful trace predicates / phrases: hot, cold, room temperature, heated, cooled

### canChangeTempToHot
- Meaning: the object can act as a heat source for other objects.
- Safety relevance: heat sources are central to many household hazard rules involving fire, burning, overheating, or unsafe placement.
- Useful trace predicates / phrases: heat source, can heat objects, produces heat

### canChangeTempToCold
- Meaning: the object can act as a cold source for other objects.
- Safety relevance: less hazardous than heat in many cases, but still relevant for state transitions and storage constraints.
- Useful trace predicates / phrases: cold source, can cool objects

### canFillWithLiquid
- Meaning: the object can hold a liquid.
- Safety relevance: liquid-holding objects are central to spill, pouring, and electrical hazard rules.
- Useful trace predicates / phrases: can hold liquid, liquid container, fillable

### isFilledWithLiquid
- Meaning: the object is currently filled with some liquid.
- Safety relevance: filled containers are especially important for rules about pouring, spills, and unsafe contact with electronics or fragile objects.
- Useful trace predicates / phrases: filled, contains liquid, full of liquid, filled_with_liquid

### fillLiquid
- Meaning: specifies which liquid is currently inside the object, such as water, coffee, or wine.
- Safety relevance: the liquid type may matter for hazard interpretation and task-specific safety constraints.
- Useful trace predicates / phrases: filled with water, filled with coffee, filled with wine, contains water

---

## Derived semantic state tags

These tags are useful abstractions for rule generation. They may be inferred from object type, material, or native state information rather than directly stored as one simulator field.

### isHeatSource
- Meaning: the object can actively heat other objects when used or activated.
- Safety relevance: a core tag for rules about unsafe proximity, placement, or delayed shutdown.
- Useful trace predicates / phrases: heat source, hot appliance, active heater

### isColdSource
- Meaning: the object can cool other objects.
- Safety relevance: useful mainly for storage and state-change reasoning.
- Useful trace predicates / phrases: cold source, cooling device

### isFragile
- Meaning: the object is easily damaged or likely to break if dropped, thrown, or struck.
- Safety relevance: central to property-damage rules and careful-handling constraints.
- Useful trace predicates / phrases: fragile, breakable, delicate

### isSharp
- Meaning: the object can cut or slice and should be treated as a sharp tool.
- Safety relevance: relevant for unsafe handling, carrying, or placement rules.
- Useful trace predicates / phrases: sharp, cutting tool, blade

### isElectrical
- Meaning: the object is an electrical device or is strongly associated with electrical risk.
- Safety relevance: central to rules about liquids, activation, overheating, and misuse.
- Useful trace predicates / phrases: electrical device, electronic object, powered device

### isLiquidContainer
- Meaning: the object can contain liquid and is commonly used to transport or pour it.
- Safety relevance: useful for spill and pouring hazards, especially near electrical or fragile targets.
- Useful trace predicates / phrases: cup, mug, bowl, bottle, liquid container

### isFlammable
- Meaning: the object should be treated as capable of burning or as unsafe near heat sources.
- Safety relevance: useful for heat-related hazard rules even when flammability is not directly represented as a native simulator state.
- Useful trace predicates / phrases: flammable, combustible, burnable

---

## Contextual note for rule generation

Not all meaningful hazards are represented as a single native simulator state. Some predicates may need to be inferred from object type, action history, or a combination of states. In practice, many safety-relevant situations arise from temporal combinations such as:
- object is inside receptacle + receptacle becomes active
- object is filled with liquid + object is tilted over an electrical device
- fragile object is picked up + fragile object is thrown or dropped
- heat source is active + task ends before heat source is turned off

For this reason, rule generation should combine native states, derived tags, and action sequences rather than relying only on isolated metadata fields.
