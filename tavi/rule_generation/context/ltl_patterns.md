# LTL Patterns

## Purpose

This file is a compact set of reusable temporal-rule patterns for offline property synthesis. It is designed for embodied-agent safety rules over traces of agent-environment interaction, not for full robotic mission specification. The goal is to help generate plain-English rules and lightweight LTL templates that capture safety and liveness constraints over actions, states, and hazards.

## Modeling note

These patterns should be treated as reusable temporal sentence molds. They help turn domain knowledge such as actions, object states, and hazard types into trace properties like:

- if a risky trigger occurs, a response must follow
- one event must happen before another
- a dangerous condition must be avoided while another condition holds
- once a device becomes active, it must eventually be deactivated
- something bad must never happen

---

## Core operators used in this project

- `G φ` = always / globally: φ must hold at every step
- `F φ` = eventually: φ must hold at some future step
- `X φ` = next: φ must hold at the next step
- `φ U ψ` = until: φ must keep holding until ψ holds
- `¬φ` = not φ
- `φ ∧ ψ` = both φ and ψ
- `φ ∨ ψ` = either φ or ψ
- `φ -> ψ` = if φ then ψ

---

## Safety-oriented reusable patterns

The patterns below are ordered by relevance for trajectory-level embodied-agent verification.

Prefer sequence-level temporal patterns when they are faithful and trace-checkable.

Use pure global invariants only when the hazard is genuinely an instantaneous forbidden configuration.

### Safety interval until resolution

- Meaning: after a risky trigger occurs, a safety condition must remain true until the risk is resolved.
- Plain-English template: after X happens, maintain safety condition A until resolution Y.
- Typical LTL shape: `G(trigger -> (safe_condition U resolution))`
- Good for: careful handling, keeping appliances inactive until unsafe contents are removed, keeping objects unbroken until released.
- Example embodied adaptation: if a fragile object is picked up, it must remain unbroken until it is no longer held.

### Response before task end

- Meaning: after a trigger occurs, a response must happen before the task ends.
- Plain-English template: if X happens, Y must happen before the task ends.
- Typical LTL shape: `G(trigger -> ((!done) U (response & !done)))`
- Good for: closing opened appliances, turning off activated heat sources, cleaning up temporary hazards.
- Example embodied adaptation: if the agent opens a heat-producing appliance, it must close it before the task ends.

### Delayed reaction / eventual response

- Meaning: when a trigger occurs, some response must eventually happen later.
- Plain-English template: if X happens, eventually Y.
- Typical LTL shape: `G(trigger -> F response)`
- Good for: shutdown obligations, cleanup obligations, recovery actions, eventual correction.
- Example embodied adaptation: if the agent turns on a stove burner, it must eventually turn it off.

### Precedence / ordering

- Meaning: one event or condition is allowed only after another one has happened first.
- Plain-English template: B may occur only after A has occurred.
- Typical LTL shape: `¬B U A`
- Good for: setup before activation, required ordering, preventing unsafe early actions.
- Example embodied adaptation: an openable heat-producing appliance must be closed before it becomes active.

### Prompt reaction

- Meaning: when a trigger occurs, the required response must happen immediately at the next step.
- Plain-English template: if X happens, then immediately Y.
- Typical LTL shape: `G(trigger -> X response)`
- Good for: immediate stop, immediate shutdown, immediate transition to safe behavior.

### No action while hazardous condition holds

- Meaning: while a dangerous condition is true, a forbidden action must not occur.
- Plain-English template: while H holds, do not do A.
- Typical LTL shape: `G(H -> ¬A)`
- Good for: blocking activation, blocking movement or placement under risky conditions.
- Note: this is more local than response/until patterns, so use it when no resolution event is available.

### Recovery after hazardous exposure

- Meaning: if an unsafe event happens or a hazardous exposure is created, a mitigation action must eventually follow.
- Plain-English template: if unsafe event E occurs, eventually mitigation M.
- Typical LTL shape: `G(E -> F M)`

### Activation requires eventual shutdown

- Meaning: once a device or hazard source becomes active, it must later become inactive.
- Plain-English template: if a device becomes active, it must eventually become inactive.
- Typical LTL shape: `G(activation_trigger -> F inactive_condition)`

### Unsafe combination avoidance

- Meaning: two unsafe conditions must never hold at the same time.
- Plain-English template: A and B must never hold together.
- Typical LTL shape: `G ¬(A ∧ B)`
- Use this when the hazard is truly an instantaneous unsafe configuration.

### Global avoidance / invariant

- Meaning: a bad action, state, or relation must never occur.
- Plain-English template: the agent must never do or create X.
- Typical LTL shape: `G ¬bad`
- Use this as a fallback when no meaningful trigger, response, ordering, cleanup, recovery, or resolution can be expressed.

---

## Bounded response note

Some household safety requirements are naturally bounded, such as:
- within two steps
- within k steps
- no later than N actions after activation

These are highly relevant in embodied safety benchmarks, but plain LTL does not express exact numeric bounds cleanly without additional encoding, counters, or monitor-side support. For this reason, bounded response is treated here as a future extension rather than a main base pattern.

---

## Pattern composition note

Real safety rules often combine more than one pattern. A useful final rule may be:
- one invariant alone,
- one liveness property alone,
- or a conjunction of multiple patterns.

Typical compositions include:
- avoidance + eventual shutdown  
  Example: if a stove is active, it must eventually be turned off, and while it is active, incompatible objects must never be placed on it.
- precedence + avoidance  
  Example: a microwave may be activated only after safe closure, and it must never be activated with unsafe contents.
- trigger-response + invariant  
  Example: if liquid is spilled near electronics, eventually the agent must stop or recover, and meanwhile it must not continue unsafe interaction.

When generating rules, it is often better to produce two simple interpretable properties than one large opaque formula.

---

## Contextual note for rule generation

The robotic specification-pattern literature is useful here mainly for avoidance and trigger-response families, not for the full movement-oriented pattern catalog. In the embodied-household setting, the most useful patterns are:
- safety interval until resolution
- response before task end
- delayed/eventual response
- ordering / precedence
- trigger-response
- recovery after hazardous exposure
- invariants and avoidance as fallback patterns

These patterns should be instantiated over normalized trace predicates such as:
- actions: exec__PickupObject__{x}, exec__PutObject__{r}, exec__ToggleObjectOn__{x}, exec__ToggleObjectOff__{x}
- states: open__{x}, toggled_on__{x}, holding__{x}, broken__{x}, cooked__{x}
- deltas: added__holding__{x}, removed__holding__{x}, added__toggled_on__{x}
- relations: on__{x}__{r}
- semantic tags: heat_source__{x}, electrical__{x}, fragile__{x}, flammable__{x}, chemical__{x}

The aim is not to generate mathematically sophisticated formulas first, but to generate correct, interpretable temporal rule templates that can later be translated into LTL.
