from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskTrace:
    """One finite task trace ready for LTL checking."""

    task_id: int | str
    scene_name: str = ""
    instruction: str = ""
    risk_category: str = ""
    status: str = ""
    success_rate: float | None = None

    # Each element is one temporal step: {atom_name: True, ...}
    steps: list[dict[str, bool]] = field(default_factory=list)


def facts_to_step(record: dict[str, Any]) -> dict[str, bool]:
    """
    Convert record["facts"] into one flloat-compatible trace step.

    Assumption:
    - Every atom listed in record["facts"] is true.
    - Therefore, no filtering is needed.

    Supported shapes:
    - {"facts": {"atom_a": true, "atom_b": true}}
    - {"facts": ["atom_a", "atom_b"]}
    """
    facts = record.get("facts") or {}

    if isinstance(facts, dict):
        return dict(facts)

    if isinstance(facts, list):
        return {atom: True for atom in facts}

    return {}


def load_traces(path: str | Path) -> list[TaskTrace]:
    """
    Load a translated JSONL trace file and split it into independent task traces.

    Interpretation:
    - task_start: metadata only, NOT a temporal step
    - normal records without record_type: real temporal steps
    - task_end: final boundary; appended as a final {"done": True} step
    - task_separator: ignored

    Returns:
        list[TaskTrace]
    """
    path = Path(path)
    traces: list[TaskTrace] = []
    current: TaskTrace | None = None

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_no}: {exc}") from exc

            record_type = record.get("record_type")

            if record_type == "task_start":
                if current is not None:
                    # Defensive: close previous malformed trace without task_end.
                    traces.append(current)

                current = TaskTrace(
                    task_id=record.get("task_id", ""),
                    scene_name=record.get("scene_name", ""),
                    instruction=record.get("instruction", ""),
                    risk_category=record.get("risk_category", ""),
                )
                continue

            if record_type == "task_end":
                if current is None:
                    # Ignore orphan task_end records.
                    continue

                current.status = record.get("status", "")
                current.success_rate = record.get("success_rate")

                # Add one finite-trace boundary step.
                # We force done=True even if the record has no facts field.
                done_step = facts_to_step(record)
                done_step["done"] = True
                current.steps.append(done_step)

                traces.append(current)
                current = None
                continue

            if record_type == "task_separator":
                continue

            # Normal step record.
            if current is None:
                # Defensive fallback for traces without task_start.
                current = TaskTrace(
                    task_id=record.get("task_id", ""),
                    scene_name=record.get("scene_name", ""),
                    instruction=record.get("instruction", ""),
                )

            step_facts = facts_to_step(record)
            current.steps.append(step_facts)

    if current is not None:
        # Defensive: include incomplete last trace if file ended unexpectedly.
        traces.append(current)

    return traces


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load translated TAVI traces.")
    parser.add_argument("trace_file", help="Path to translated JSONL trace file")
    args = parser.parse_args()

    loaded = load_traces(args.trace_file)

    print(f"Loaded {len(loaded)} task traces")
    for trace in loaded:
        print(
            f"task_id={trace.task_id} | steps={len(trace.steps)} | "
            f"risk={trace.risk_category!r} | instruction={trace.instruction!r}"
        )