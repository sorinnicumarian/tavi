# AI2-THOR Actions

## Purpose

This file is a compact action vocabulary for offline rule generation. It describes the main actions an embodied agent can perform in AI2-THOR at the level needed for temporal safety rule synthesis: what each action means, what kind of world change it can cause, and why it matters for safety reasoning.

## Modeling note

For rule generation, actions should be understood as symbolic events that may appear in a trace, such as `agent picks up knife`, `agent opens microwave`, or `agent turns on stove`. The focus here is not API syntax, but action meaning and likely state effects.

---

## Navigation actions

### MoveAhead / MoveBack / MoveLeft / MoveRight
- Category: navigation
- Meaning: the agent changes its position in the scene relative to its current orientation.
- Effects: the agent moves to a different location and may gain or lose visibility and reachability of nearby objects.
- Safety relevance: navigation brings the agent closer to hazards, enables later interactions, and can change whether dangerous objects or devices become reachable.
- Useful trace verbs: move, approach, go to, navigate, reposition

### RotateLeft / RotateRight
- Category: navigation
- Meaning: the agent changes the direction it is facing.
- Effects: the agent's orientation changes, which changes what it can see and interact with.
- Safety relevance: often enables later interactions with hazardous objects or appliances by bringing them into view and reach.
- Useful trace verbs: rotate, turn, face, orient

### LookUp / LookDown
- Category: navigation
- Meaning: the agent changes the vertical direction of its camera.
- Effects: the agent sees a different vertical portion of the scene and may expose new objects for later interaction.
- Safety relevance: mainly an enabling action; it can expose objects or devices that become part of a later hazardous sequence.
- Useful trace verbs: look up, look down, inspect, view

### Crouch / Stand
- Category: navigation
- Meaning: the agent changes between a lower and higher body posture.
- Effects: the agent's viewpoint and interaction geometry change, which can affect what objects are visible or reachable.
- Safety relevance: mainly an enabling action that can make low or high objects accessible in later risky sequences.
- Useful trace verbs: crouch, lower, stand, rise, adjust posture

### Done
- Category: navigation
- Meaning: the agent declares that it has finished the current task.
- Effects: no direct world change; marks a terminal task event from the agent's point of view.
- Safety relevance: useful for termination-style rules, such as requiring a device to be turned off before task completion.
- Useful trace verbs: finish, complete, stop, end task

---

## Manipulation actions

### PickupObject
- Category: manipulation
- Meaning: the agent takes an object into its hand and starts carrying it.
- Effects: the object becomes held by the agent and can be transported to other locations or receptacles.
- Safety relevance: enables transport of dangerous, fragile, hot, sharp, spillable, or electrically sensitive objects.
- Useful trace verbs: pick up, grasp, hold, carry, take

### PutObject
- Category: manipulation
- Meaning: the agent places the currently held object into or onto another object that acts as a receptacle or support surface.
- Effects: the held object changes location or containment relation, such as being placed on a counter or inside a microwave.
- Safety relevance: critical for hazards involving placement near heat, water, electrical devices, fragile surfaces, or other unsafe contexts.
- Useful trace verbs: put, place, set down, insert, store

### DropHandObject
- Category: manipulation
- Meaning: the agent releases the currently held object without deliberately placing it on a chosen target.
- Effects: the object is no longer held and falls or lands according to the scene physics.
- Safety relevance: can cause spills, breakage, collisions, or loss of control over dangerous or fragile objects.
- Useful trace verbs: drop, release, let fall

### ThrowObject
- Category: manipulation
- Meaning: the agent throws the currently held object forward with force.
- Effects: the object is projected through the scene and may collide with other objects or surfaces.
- Safety relevance: directly relevant to breakage, damage, collisions, and unsafe handling of sharp, heavy, or fragile objects.
- Useful trace verbs: throw, hurl, launch, toss

### MoveHeldObject
- Category: manipulation
- Meaning: the agent repositions the object it is currently holding.
- Effects: the held object changes pose relative to the agent, which can prepare later placement, dropping, or pouring-like behavior.
- Safety relevance: helps create precise hazardous setups, such as bringing a held object close to a heat source, liquid target, or fragile item.
- Useful trace verbs: move, reposition, align, bring closer

### RotateHeldObject
- Category: manipulation
- Meaning: the agent rotates the object it is currently holding.
- Effects: the held object changes orientation; for fillable containers, rotation can lead to emptying or spill-like behavior.
- Safety relevance: relevant for pouring, spilling, and other context-sensitive hazards caused by changing object orientation.
- Useful trace verbs: rotate, tilt, turn, invert

### DirectionalPush / PushObject / PullObject
- Category: manipulation
- Meaning: the agent applies force to an object to move it without picking it up.
- Effects: the target object changes position through physical motion.
- Safety relevance: can move dangerous or fragile objects into unsafe places, knock items over, or trigger collisions.
- Useful trace verbs: push, pull, shove, move, displace

### TouchThenApplyForce
- Category: manipulation
- Meaning: the agent touches an object at a chosen point and applies force to it.
- Effects: the touched object may move, tip, or collide with other objects.
- Safety relevance: can create indirect hazards by physically disturbing objects even when they are not picked up.
- Useful trace verbs: touch, press, apply force, strike

---

## State-change actions

### OpenObject
- Category: state change
- Meaning: the agent opens an openable object such as a fridge, microwave, cabinet, or drawer.
- Effects: the target object changes from closed to open, making its contents or interior accessible.
- Safety relevance: opening can expose dangerous contents, make later placement possible, or enable later hazardous action sequences.
- Useful trace verbs: open, access, expose, uncover

### CloseObject
- Category: state change
- Meaning: the agent closes an openable object.
- Effects: the target object changes from open to closed.
- Safety relevance: often appears in temporal rules where an object must be closed after use or before turning on a device.
- Useful trace verbs: close, shut, seal

### ToggleObjectOn
- Category: state change
- Meaning: the agent turns a toggleable object on.
- Effects: the target enters an active state; depending on the object, this can activate heat, electricity, light, water flow, or another ongoing process.
- Safety relevance: one of the most important actions for safety rule generation because it can activate hazardous appliances or processes.
- Useful trace verbs: turn on, switch on, activate, start

### ToggleObjectOff
- Category: state change
- Meaning: the agent turns a toggleable object off.
- Effects: the target leaves its active state and stops its ongoing process.
- Safety relevance: essential for shutdown and recovery rules, especially for heat sources, electrical devices, and water-related devices.
- Useful trace verbs: turn off, switch off, deactivate, stop

### BreakObject
- Category: state change
- Meaning: the agent causes a breakable object to become broken.
- Effects: the target enters a damaged state that is typically irreversible during the episode.
- Safety relevance: directly represents property damage and may also create secondary hazards such as sharp fragments or unusable devices.
- Useful trace verbs: break, smash, shatter, damage

### SliceObject
- Category: state change
- Meaning: the agent slices a sliceable object into a sliced form.
- Effects: the original object changes into one or more sliced objects; the change is typically irreversible during the episode.
- Safety relevance: relevant when rule generation involves knives, food preparation, or sequencing constraints around cutting actions.
- Useful trace verbs: slice, cut, chop

### CookObject
- Category: state change
- Meaning: the agent causes a cookable object to become cooked.
- Effects: the target enters a cooked state; this can also be achieved indirectly through contextual heating.
- Safety relevance: relevant for rules about heating, cooking, fire-adjacent actions, and leaving heat sources active.
- Useful trace verbs: cook, heat, prepare, warm

---

## Brief query actions

These actions are mainly for perception or planning support. They usually do not directly create hazards, so they are less important for rule generation than navigation, manipulation, and state-change actions.

### GetObjectInFrame
- Category: query
- Meaning: identifies which object appears at a chosen point in the current view.
- Effects: no direct world change; yields object identity information.
- Safety relevance: low direct relevance; mainly supports object grounding before later actions.
- Useful trace verbs: identify, localize, inspect

### GetCoordinateFromRaycast
- Category: query
- Meaning: retrieves a world coordinate corresponding to a point in the current view.
- Effects: no direct world change; yields spatial information.
- Safety relevance: low direct relevance; mainly supports spatial grounding for later interactions.
- Useful trace verbs: locate, estimate position, ground

### GetReachablePositions
- Category: query
- Meaning: returns positions the agent can navigate to.
- Effects: no direct world change; yields navigational possibilities.
- Safety relevance: low direct relevance; useful only as background for reachability or access constraints.
- Useful trace verbs: find reachable place, plan route, determine access

### GetInteractablePoses
- Category: query
- Meaning: returns agent poses from which an object can be interacted with.
- Effects: no direct world change; yields interaction opportunities.
- Safety relevance: low direct relevance; useful only as background knowledge for later interactions.
- Useful trace verbs: find pose, position for interaction, prepare access

---

## Contextual note for rule generation

In AI2-THOR, many hazards arise from action sequences rather than a single action alone. For example, placing an object in or on a device and then turning that device on can create a new hazardous state. For this reason, rule generation should focus not only on isolated actions, but also on meaningful temporal combinations such as:
- pick up -> carry -> put
- open -> put -> close -> turn on
- turn on -> leave active -> finish task
- pick up container -> rotate held object -> spill-like effect

