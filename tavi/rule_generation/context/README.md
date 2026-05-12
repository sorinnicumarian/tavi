# README

The `context/` folder contains the background knowledge used in the **offline rule-synthesis step** of the project **Verification of Embodied AI Agents**.

## Files in this folder

#### `ai2thor_actions.md`

This file contains a compact action vocabulary for AI2-THOR.

#### `ai2thor_object_states.md`

This file contains a compact vocabulary of object states and state relations that matter for safety reasoning.

#### `hazards_types.md`

This file defines the hazard taxonomy used for rule generation.

#### `ltl_patterns.md`

This file contains a small library of reusable temporal-rule patterns that are useful for embodied-agent safety rules.

#### `rule_generation_prompt.md`

This file contains the actual prompt template used in the offline LLM rule-generation step.

It tells the model:
- what its job is,
- which files it must use,
- what a good rule looks like,
- what kinds of rules to avoid,
- which temporal pattern families to prefer,
- how many rules to generate,
- and how to format the output.

## Note
The markdown files are generated using OpenAI's ChatGPT 5.4 with extened thinking enabled, and manually modified to better fit the current context of the project.