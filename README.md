# TAVI
Temporal Agents Verification Interface — trajectory-level safety verification of embodied AI agents using LTL/CTL temporal logic.

RP5.3 research project, Polimi. Supervisor: Matteo Camilli.

---

## 1. Intro

### What it does

An agent moves around a simulated home and performs tasks — pick up a knife, turn on the stove, etc. TAVI records every step as a structured trace, then checks those traces against safety rules, e.g. *"if the agent ever picks up a flammable object, it must never afterwards be near a heat source."*

### Why it exists

Existing tools like AgentSpec only check one action at a time. They can't answer "did the agent ever hold a knife while standing near a child?" — that requires reasoning over a full sequence of steps. TAVI is being built to do that.

### Current state (v0.2)

Right now TAVI only does step 1: recording. It runs a hardcoded sequence of actions in a simulated kitchen, and writes every step to a JSONL trace file with the world state and facts. The checker, rule translator, and runtime monitor are not built yet.

TAVI currently covers trace collection and autonomous agent execution:

- **`scenario_1_hardcoded`** — a fixed action sequence that navigates to a knife, picks it up, and drops it. Useful as a baseline.
- **`scenario_2_autonomous`** — a Gemini 2.5 Flash agent that observes the scene at each step and decides actions autonomously. The LLM receives visible objects, current facts, and action history, and responds with the next action.

Both scenarios write a JSONL trace to `traces/`. The checker, rule translator, and runtime monitor are not built yet.

To select which scenarios run, edit `SCENARIOS_TO_RUN` in `tavi/main.py` and comment out what you don't need.

### Key concepts

**Propositions** — instead of saving the full raw simulator state (hundreds of fields), we extract simple true/false facts about the world at each step: `holding(knife)`, `near(stove)`, `on(knife,countertop)`. These are grounded in the simulator — they come directly from AI2-THOR's object metadata. They're the vocabulary that safety rules are written against.

**LTL / CTL** — temporal logic languages for writing safety rules over sequences of propositions. LTL (Linear Temporal Logic) reasons over a single timeline; CTL (Computation Tree Logic) can reason over branching futures. Example LTL rule: `G(holding(knife) → F ¬near(child))` — *"globally, whenever the agent holds a knife, it must eventually no longer be near a child."* These are checked against the recorded trace, not in real time (for now).


### How it works

```
  AI2-THOR (Unity, runs locally)
       ↓  executes actions, returns scene metadata
  trace_collector
       ↓  extracts propositions, writes one JSONL line per step
  traces/<scenario_name>.jsonl
       ↓  (future) checked against LTL/CTL safety rules
  violations report
```

**AI2-THOR** ([Kolve et al., 2017](https://arxiv.org/abs/1712.05474)) is a 3D home simulator. It runs locally and exposes a Python API. It only accepts discrete actions — `MoveAhead`, `RotateRight`, `PickupObject`, etc. — not natural language. Docs: [navigation](https://ai2thor.allenai.org/ithor/documentation/navigation) · [full reference](https://ai2thor.allenai.org/ithor/documentation).

**trace_collector** wraps AI2-THOR directly. It intercepts every action, snapshots the world state before and after, extracts propositions, and appends a JSONL line.

---

## 2. Setup

### 1. Install Ollama

Download from [ollama.com](https://ollama.com), then pull a model:

```bash
ollama pull llama3.1:8b
```

### 2. Clone the repo

```bash
git clone <tavi-repo-url>
cd tavi
```

### 3. Python environment

**macOS:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Environment variables

```bash
cp .env.example .env
```

Fill in `GEMINI_API_KEY` for benchmark runs. Never commit `.env`.

---

## 3. Run

```bash
source .venv/bin/activate
python -m tavi.main
```

Loads a kitchen scene in AI2-THOR, navigates to a knife, picks it up, and drops it. A window shows the simulation. Each step is printed in the terminal and written to `traces/run.jsonl`.

Runs all scenarios listed in `SCENARIOS_TO_RUN` in `tavi/main.py`. Each scenario writes its trace to `traces/<scenario_name>.jsonl`. A window shows the simulation; steps are printed in the terminal.

First run downloads the Unity binary (~1GB) — takes a few minutes, cached after that.

### Scenarios

| Scenario | Description |
|---|---|
| `scenario_1_hardcoded` | Fixed action sequence — navigates to knife, picks it up, drops it |
| `scenario_2_autonomous` | Gemini 2.5 Flash agent — observes scene and decides actions autonomously, but same goal as 1 |

Comment out entries in `SCENARIOS_TO_RUN` to skip them.

---

## 4. Next steps

- **SafeAgentBench** — a benchmark of 750 tasks covering 10 hazard categories (fire, sharp objects, chemicals, etc.), built on top of AI2-THOR by a team at SJTU. Repo: [github.com/shengyin1224/SafeAgentBench](https://github.com/shengyin1224/SafeAgentBench). The plan is to plug this in as the task source and run the trace collector across all 750 tasks, giving us a large dataset of real hazardous traces to check properties against.
- **Rule translator** — LLM takes a plain English safety rule and outputs an LTL/CTL formula automatically, using the proposition vocabulary from the trace. Writing formulas by hand is tedious; this automates it. We'll also use the 22 reusable patterns from [Specification Patterns for Robotic Missions (2019)](Docs/Papers/4.%20Specification%20Patterns%20for%20Robotic%20Missions.pdf) as templates.
- **Trace checker** — reads a JSONL trace and checks it against LTL/CTL formulas, reporting any violations.
- **Violation reporter** — highlights the exact steps where a violation occurred and explains it in plain English.
- **Runtime monitor** — checks properties in real time and interrupts the agent before it does something unsafe.
