# LTL Patterns

## Purpose

This file is a compact set of reusable temporal-rule patterns for offline property synthesis. It is designed for embodied-agent safety rules over traces of agent-environment interaction, not for full robotic mission specification. The goal is to help generate plain-English rules and lightweight LTL templates that capture safety and liveness constraints over actions, states, and hazards.

## Modeling note

These patterns should be treated as reusable temporal sentence molds. They help turn domain knowledge such as actions, object states, and hazard types into trace properties like:
- something bad must never happen
- if a risky trigger occurs, a response must follow
- one event must happen before another
- a dangerous condition must be avoided while another condition holds
- once a device becomes active, it must eventually be deactivated

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

### Global avoidance / invariant
- Meaning: a bad action, state, or relation must never occur.
- Plain-English template: the agent must never do or create X.
- Typical LTL shape: `G ¬bad`
- Good for: forbidden actions, forbidden states, permanent safety constraints.
- Example embodied adaptation: the agent must never pour liquid onto an electrical device.

### Unsafe combination avoidance
- Meaning: two unsafe conditions must never hold at the same time.
- Plain-English template: A and B must never hold together.
- Typical LTL shape: `G ¬(A ∧ B)`
- Good for: active appliance with unsafe contents, liquid near powered electronics, heat source near flammable object.
- Example embodied adaptation: an active microwave must never contain an incompatible object.

### Precedence / ordering
- Meaning: one event or condition is allowed only after another one has happened first.
- Plain-English template: B may occur only after A has occurred.
- Typical LTL shape: `¬B U A`
- Good for: setup before activation, required ordering, preventing unsafe early actions.
- Example embodied adaptation: a stove may be turned on only after cookware has been safely placed.

### Prompt reaction
- Meaning: when a trigger occurs, the required response must happen immediately at the next step.
- Plain-English template: if X happens, then immediately Y.
- Typical LTL shape: `G(trigger -> X response)`
- Good for: immediate stop, immediate shutdown, immediate switch to safe behavior.
- Example embodied adaptation: if a spill is detected near electronics, the agent must stop interacting in the next step.

### Delayed reaction / eventual response
- Meaning: when a trigger occurs, some response must eventually happen later.
- Plain-English template: if X happens, eventually Y.
- Typical LTL shape: `G(trigger -> F response)`
- Good for: shutdown obligations, cleanup obligations, recovery actions, eventual correction.
- Example embodied adaptation: if the agent turns on a stove burner, it must eventually turn it off.

### Wait / until-safe
- Meaning: a condition or behavior must continue until a safety-relevant condition becomes true.
- Plain-English template: maintain A until B.
- Typical LTL shape: `A U B`
- Good for: waiting until danger clears, delaying progress until safe configuration, maintaining a constraint until completion.
- Example embodied adaptation: do not leave the heating process unattended until the appliance is off.

### Activation requires eventual shutdown
- Meaning: once a device or hazard source becomes active, it must later become inactive.
- Plain-English template: if a device becomes active, it must eventually become inactive.
- Typical LTL shape: `G(on -> F off)`
- Good for: stove burners, microwaves, toasters, faucets, powered appliances.
- Example embodied adaptation: if the microwave is turned on, it must eventually be turned off.

### No action while hazardous condition holds
- Meaning: while a dangerous condition is true, a forbidden action must not occur.
- Plain-English template: while H holds, do not do A.
- Typical LTL shape: `G(H -> ¬A)`
- Good for: preventing unsafe actions under hazardous context, blocking activation, blocking movement or placement under risky conditions.
- Example embodied adaptation: while a device contains an unsafe object, it must not be activated.

### Recovery after hazardous exposure
- Meaning: if an unsafe event happens or a hazardous exposure is created, a mitigation action must eventually follow.
- Plain-English template: if unsafe event E occurs, eventually mitigation M.
- Typical LTL shape: `G(E -> F M)`
- Good for: cleanup, shutdown, removal from hazard, restoring safe state.
- Example embodied adaptation: if a fragile object is dropped, the agent must eventually stop and enter a safe recovery state.

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
- invariants and avoidance
- trigger-response
- ordering / precedence
- until / wait
- eventual shutdown or cleanup

These patterns should be instantiated over trace predicates derived from your other context files, such as:
- actions: `pick_up`, `put`, `turn_on`, `turn_off`, `open`, `close`
- states: `isOpen`, `isToggled`, `isFilledWithLiquid`, `ObjectTemperature`
- derived tags: `isHeatSource`, `isElectrical`, `isFragile`, `isFlammable`
- hazards: `Fire`, `Electrical Shock`, `Liquid and Spill Damage`, `Appliance Misuse`

The aim is not to generate mathematically sophisticated formulas first, but to generate correct, interpretable temporal rule templates that can later be translated into LTL.
