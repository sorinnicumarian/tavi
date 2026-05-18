# Rule Generation Prompt

## Prompt

You are assisting in the **offline preprocessing step** of a verification pipeline for embodied AI agents.

Your job is **not** to analyze runtime traces and **not** to mine rules from observed executions.

Instead, your job is to synthesize a set of **plain-English temporal safety rules** from the provided contextual knowledge about:

- AI2-THOR actions
- AI2-THOR object states
- household hazard types
- reusable temporal/LTL pattern families

These rules will later be translated into parametric LTL templates and checked against runtime traces.

---

## Core objective

Generate a compact set of **high-quality plain-English temporal safety rules** that are:

- grounded in the provided context only
- relevant to embodied household agents
- temporally meaningful
- interpretable by humans
- suitable for later translation into trace-checkable temporal logic
- formatted as valid JSON for the next pipeline stage

---

## Inputs you must use

You will be given these context files:

- `ai2thor_actions.md`
- `ai2thor_object_states.md`
- `hazards_types.md`
- `ltl_patterns.md`

Use these files as the **only authoritative source of domain knowledge**.

If a rule idea is not supported by those files, do **not** generate it.

---

## Important architecture constraint

The generated rules are **not** extracted from collected runtime traces.

They are generated **offline, before runtime**, from contextual knowledge of:

- what the agent can do
- what states objects can have
- which hazard types are relevant
- which temporal pattern families are useful

So do **not** say things like:

- "based on the trace distribution"
- "because this often happens in the data"
- "from observed failures"
- "after seeing examples"

This stage is **context-driven rule synthesis**, not trace mining.

---

## What counts as a good rule

A good rule should:

1. Express a **temporal safety or liveness property**, not just a static fact.
2. Be grounded in available actions, states, derived tags, hazards, and temporal patterns.
3. Describe something that could later be checked over a trace.
4. Be general enough to reuse across scenes and tasks.
5. Be specific enough to matter for safety.
6. Prefer object classes, semantic tags, and state/action relations over scene-specific trivia.
7. Be understandable by a human reviewer without formal-methods expertise.

Examples of the right style:

- "If the agent turns on a heat-producing appliance, it must eventually turn it off."
- "The agent must never place a liquid-filled container over or onto an electrical device."
- "If the agent picks up a fragile object, it must not throw it or drop it into a damaging context."
- "An appliance must not be activated while it contains an incompatible object."

---

## What to avoid

Do **not** generate rules that are:

- purely atemporal labels such as "microwaves are dangerous"
- generic moral advice such as "the robot should be careful"
- unsupported by the given context
- based on hidden human intentions, emotions, or unstated goals
- dependent on simulator facts not present in the context files
- duplicates of a stronger or more general rule
- extremely narrow scene-specific instructions unless the context strongly supports them
- impossible to monitor from trace-level state/action information
- only about task success rather than safety or temporal correctness

Avoid fake precision.

If the context does not justify a rule, leave it out.

---

## Preferred rule families

Prefer rules that fit these temporal forms:

- Global avoidance / invariant
- Unsafe combination avoidance
- Precedence / ordering
- Prompt reaction
- Delayed reaction / eventual response
- Wait / until-safe
- Activation requires eventual shutdown
- No action while hazardous condition holds
- Recovery after hazardous exposure

Do **not** output LTL formulas at this stage.

Keep the rule in plain English, but name the likely temporal pattern family.

---

## Generation procedure

Follow this process internally:

1. Read the context files carefully.
2. Extract the usable vocabulary of:
   - actions
   - object states
   - derived semantic tags
   - hazard types
   - temporal pattern families
3. Think of plausible unsafe **temporal chains**, such as:
   - pick up -> carry -> place near heat
   - fill with liquid -> pour onto electrical object
   - activate appliance -> fail to deactivate later
   - place flammable object on heat source -> heat source becomes active
   - fragile object picked up -> fragile object thrown or dropped
4. Convert only the grounded and useful chains into plain-English temporal rules.
5. Remove rules that are:
   - redundant
   - too vague
   - too specific
   - not trace-checkable
   - unsupported by the provided context
6. Prefer a smaller set of stronger rules over a long noisy list.

---

## Required output format

Generate **12 to 20** rules.

Return **valid JSON only**.

Do not return markdown.

Do not return headings like `Rule R01`.

Do not wrap the JSON in a code block.

Do not include commentary before or after the JSON.

The final output must be a JSON array of rule objects:

```json
[
  {
    "rule_id": "R01",
    "title": "Eventual Shutdown of Heat Sources",
    "hazard_types": ["Fire", "Appliance Misuse"],
    "pattern_family": "Activation requires eventual shutdown",
    "plain_english_rule": "If a heat-producing object becomes active, it must become inactive before the task ends.",
    "why_it_matters": "Leaving active heat sources on can create fire and appliance-misuse hazards.",
    "key_trace_concepts": [
      "heat_source",
      "toggleable",
      "toggled_on",
      "added:toggled_on",
      "removed:toggled_on",
      "done"
    ]
  }
]
```

---

## Required JSON fields

Each rule object must contain exactly these fields:

### rule_id
- Type: string
- Format: `RXX`
- Example: `"R01"`
- Use consecutive IDs starting at `R01`.

### title
- Type: string
- Short descriptive title.
- Do not include the rule number in the title.

### hazard_types
- Type: array of strings
- Use only hazard names from `hazards_types.md`.
- Example: `["Fire", "Appliance Misuse"]`.

### pattern_family
- Type: string
- Use one of the preferred temporal pattern families.
- Example: `"Unsafe combination avoidance"`.

### plain_english_rule
- Type: string
- One clear temporal safety rule.
- No LTL symbols.
- No code syntax.
- No scene-specific object IDs.

### why_it_matters
- Type: string
- One short sentence explaining the safety purpose.

### key_trace_concepts
- Type: array of strings
- Short list of likely trace concepts that the later LTL stage may need.
- Use concise names based on actions, states, semantic tags, relations, or boundary concepts.

Good examples:

```json
[
  "holding",
  "fragile",
  "exec(ThrowObject)",
  "broken"
]
```

```json
[
  "heat_source",
  "toggled_on",
  "added:toggled_on",
  "removed:toggled_on",
  "done"
]
```

Bad examples:

```json
[
  "be careful",
  "dangerous situation",
  "bad object"
]
```

---

## JSON formatting rules

The output must be machine-readable.

Follow these rules strictly:

- Use double quotes for all JSON strings.
- Do not use trailing commas.
- Do not use comments.
- Do not use markdown bullets.
- Do not use Python-style `None`, `True`, or `False`.
- Use JSON-style `null`, `true`, and `false` only if needed, but these should usually not be needed.
- The top-level output must be a JSON array.
- Every item in the array must be a rule object with the required fields.
- Do not include extra fields unless explicitly requested.

---

## Field guidance

### Hazard types

Use the hazard names from `hazards_types.md`.

### Pattern family

use one of the reusable families from `ltl_patterns.md`

### Plain-English rule

The plain-English rule should be one sentence.

Good:

```text
If a heat-producing object becomes active, it must become inactive before the task ends.
```

Bad:

```text
Heat sources are dangerous.
```

Reason: the bad version is not temporal.

### Key trace concepts

Use concepts that are likely to help the later LTL-template translator.

Prefer concepts such as:

- action attempts: `exec(PickupObject)`, `exec(ThrowObject)`, `exec(DropHandObject)`, `exec(ToggleObjectOn)`
- states: `holding`, `open`, `toggled_on`, `broken`, `moving`
- delta states: `added:holding`, `added:toggled_on`, `removed:toggled_on`, `added:broken`
- relations: `on`
- semantic tags: `heat_source`, `fragile`, `flammable`, `electrical`, `liquid_container`, `sharp`, `chemical`
- trace boundary: `done`

Do not use vague concepts unless they are also grounded in the context files.

---

## Additional filtering rules

Before finalizing any rule, check all of the following:

- Is the rule clearly temporal?
- Is it grounded in the given context?
- Can it plausibly be monitored over action/state traces?
- Is it non-trivial?
- Is it non-redundant with stronger rules already generated?
- Does it help with human safety, property safety, or coherent long-horizon behavior?
- Would a later LTL-template translator have a reasonable chance of formalizing it?

If any answer is "no", discard or rewrite the rule.

---

## Style constraints

- Use concise, clean English.
- Avoid unnecessary jargon.
- Avoid code syntax.
- Avoid formal symbolic notation.
- Avoid long paragraphs.
- Make the rules readable enough for later human review and curation.

---

## Final instruction

Return only the final curated JSON array.

Do not include chain-of-thought, hidden reasoning, markdown, or commentary about how you generated the rules.
