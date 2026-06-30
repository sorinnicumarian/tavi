import json
import re
import os
from pathlib import Path

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "traces",
    "safeagentbench_abstract_traces.jsonl"
)

OUTPUT_FILE = os.path.join(
    _REPO_ROOT,
    "traces",
    "safeagentbench_abstract_traces_translated.jsonl"
)


def predicate_to_key(predicate: str) -> str | None:
    """
    Converts:

        flammable(cloth_1)
    ->  flammable__cloth_1

        on(candle_1,bathtub_1)
    ->  on__candle_1__bathtub_1

        material(candle_1,wax)
    ->  material__candle_1__wax

    Returns None for has_position facts.
    """

    predicate = predicate.strip()

    # Remove all has_position facts
    if predicate.startswith("has_position("):
        return None

    match = re.match(r"([^(]+)\((.*)\)", predicate)

    if not match:
        return None

    pred_name = match.group(1).strip()
    args = [arg.strip() for arg in match.group(2).split(",")]

    return pred_name + "__" + "__".join(args)


def to_pascal_case(text: str) -> str:
    """
    find candle -> FindCandle
    open cabinet -> OpenCabinet
    """

    return "".join(word.capitalize() for word in text.split())


def convert_json(old_data: dict) -> dict:
    """
    Convert one trace entry from old format to new format.
    """

    new_data = {}

    # Copy everything except fields we transform
    for key, value in old_data.items():
        if key not in {"facts", "facts_delta", "exec"}:
            new_data[key] = value

    facts_dict = {}

    # ==========================================================
    # Convert facts
    # ==========================================================
    for fact in old_data.get("facts", []):

        fact = fact.strip()

        # Remove has_position(...)
        if fact.startswith("has_position("):
            continue

        # Remove exec(...) entries from facts
        if fact.startswith("exec("):
            continue

        key = predicate_to_key(fact)

        if key is not None:
            facts_dict[key] = True

    # ==========================================================
    # Convert facts_delta
    # ==========================================================
    facts_delta = old_data.get("facts_delta", {})

    # Added facts
    for added_fact in facts_delta.get("added", []):

        added_fact = added_fact.strip()

        if added_fact.startswith("has_position("):
            continue

        if added_fact.startswith("exec("):
            continue

        key = predicate_to_key(added_fact)

        if key is not None:
            facts_dict[f"added__{key}"] = True

    # Removed facts
    for removed_fact in facts_delta.get("removed", []):

        removed_fact = removed_fact.strip()

        if removed_fact.startswith("has_position("):
            continue

        if removed_fact.startswith("exec("):
            continue

        key = predicate_to_key(removed_fact)

        if key is not None:
            facts_dict[f"removed__{key}"] = True

    # ==========================================================
    # Convert exec field
    # exec(ToggleObjectOn,candle_1) -> exec__ToggleObjectOn__candle_1
    # exec(DropHandObject)          -> exec__DropHandObject
    # None (dropped actions)        -> skip
    # ==========================================================
    exec_string = old_data.get("exec")

    if exec_string:
        match = re.match(r"exec\(([^,)]+)(?:,([^)]+))?\)", exec_string)
        if match:
            action_part = match.group(1).strip()
            object_part = match.group(2).strip() if match.group(2) else None
            if object_part:
                new_data[f"exec__{action_part}__{object_part}"] = True
            else:
                new_data[f"exec__{action_part}"] = True

    # Replace facts list with facts dictionary (done marker set by caller)
    new_data["facts"] = facts_dict

    return new_data


def get_steps_with_history(
    trace_file=OUTPUT_FILE,
    task_id=None,
):
    """
    Yields (step, history) tuples.

    history contains all previous steps for the same task,
    including the current step.
    """

    histories = {}

    with open(trace_file, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            if record.get("record_type") in (
                "task_start",
                "task_end",
                "task_separator",
            ):
                continue

            current_task = record.get("task_id")

            if task_id is not None and current_task != task_id:
                continue

            if current_task not in histories:
                histories[current_task] = []

            histories[current_task].append(record)

            # Return current step and all previous steps
            yield record, histories[current_task].copy()
            
def get_steps(
    trace_file: str = OUTPUT_FILE,
    task_id: int | None = None,
    step_id: int | None = None,
):
    """
    Yields translated step dicts from a trace file.

    Args:
        trace_file: path to the translated JSONL (default: OUTPUT_FILE)
        task_id:    if given, only yield steps for that task
        step_id:    if given, only yield the step with that step_id
                    (within the task_id filter if also set)

    Yields dicts with keys: task_id, step_id, action, facts, outcome, …
    Skips task_start / task_end / task_separator records.

    Example:
        for step in iter_steps(task_id=1, step_id=0):
            print(step["facts"])
    """
    with open(trace_file, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record.get("record_type") in ("task_start", "task_end", "task_separator"):
                continue
            if task_id is not None and record.get("task_id") != task_id:
                continue
            if step_id is not None and record.get("step_id") != step_id:
                continue
            yield record


# ----------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------
def main(input_file: str = INPUT_FILE, output_file: str = OUTPUT_FILE):

    with open(input_file, "r", encoding="utf-8") as fin:
        raw_lines = [json.loads(line) for line in fin]

    # Find the last step_id per task so done=True is set only there
    last_step: dict[int, int] = {}
    for record in raw_lines:
        if record.get("record_type") in ("task_start", "task_end", "task_separator"):
            continue
        tid = record.get("task_id")
        sid = record.get("step_id", -1)
        if tid is not None and sid > last_step.get(tid, -1):
            last_step[tid] = sid

    with open(output_file, "w", encoding="utf-8") as fout:
        for record in raw_lines:
            new_data = convert_json(record)
            tid = record.get("task_id")
            sid = record.get("step_id")
            is_last = (
                tid is not None
                and sid is not None
                and last_step.get(tid) == sid
            )
            new_data["facts"]["done"] = is_last
            fout.write(json.dumps(new_data) + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=INPUT_FILE)
    parser.add_argument("--output", default=None,
        help="Output path (default: auto-derived from input)")
    cli = parser.parse_args()
    out = cli.output or cli.input.replace("_traces.jsonl", "_traces_translated.jsonl")
    main(cli.input, out)
    print(f"Translated: {cli.input} -> {out}")
