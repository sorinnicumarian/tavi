# SafeAgentBench Task Sets

Source: [SafeAgentBench](https://github.com/shengyin1224/SafeAgentBench) — 750 tasks across 10 hazard categories in AI2-THOR domestic environments.

Each file is a JSONL where every line is one task with fields:
- `scene_name` — AI2-THOR floor plan (e.g. `FloorPlan401`)
- `instruction` — what the agent is asked to do
- `risk_category` — hazard type (Fire, Electrical Shock, Explosion, etc.)
- `step` — ground-truth low-level action sequence
- `final_state` — expected object states after completion (used for evaluation)

## Files

| File | Tasks | Description |
|---|---|---|
| `safeagentbench_abstract_tasks.jsonl` | 100 | Hazardous instructions phrased vaguely — agent must infer the danger |
| `safeagentbench_unsafe_tasks.jsonl` | 300 | Explicit hazardous instructions across all 10 hazard categories |
| `safeagentbench_safe_tasks.jsonl` | 300 | Safe instructions — control group for measuring false positives |
| `safeagentbench_long_horizon_tasks.jsonl` | 50 | Multi-step tasks where the hazard is implicit and time-delayed |

## Trace output

Running `python -m tavi.main` processes `safeagentbench_abstract_tasks.jsonl` by default and writes to `traces/safeagentbench_abstract_traces.jsonl`. Change `INPUT_FILE` in `main.py` to run a different set.
