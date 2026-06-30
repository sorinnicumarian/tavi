import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# allow running as `python tavi/main.py` in addition to `python -m tavi.main`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jsonlines
from dotenv import load_dotenv

from ai2thor.controller import Controller
from tavi.simulation.planner.map_vlm import run_map
from tavi.traces.trace_collector import TraceCollector

load_dotenv()

log = logging.getLogger(__name__)


class SafetyViolation(Exception):
    """Raised by the runtime monitor when an LTL rule is violated."""
    def __init__(self, message: str, violations: list):
        super().__init__(message)
        self.violations = violations


def _build_monitor(rules: list, object_ids: list[str], log_path: str):
    """
    Returns an on_step callback for TraceCollector.

    The callback receives the already-translated step record (same format as the
    translated JSONL). Accumulates steps and checks LTL rules after each one.
    Raises SafetyViolation if any rule is violated.
    """
    from tavi.rule_checker.main import check_rules

    accumulated: list[dict] = []

    def monitor(translated: dict) -> bool:
        # done is only True at task end — intermediate steps are never done
        translated["facts"]["done"] = False
        accumulated.append(translated)

        violated, message, violations, _ = check_rules(
            accumulated, task_id=translated.get("task_id"), rules=rules, object_ids=object_ids
        )

        if violated:
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": translated.get("task_id"),
                "step_id": translated.get("step_id"),
                "message": message,
                "violations": violations,
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            print(f"\n🚨 SAFETY VIOLATION at step {translated.get('step_id')}: {message}")
            raise SafetyViolation(message, violations)

        return True

    return monitor

_SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "simulation", "scenarios")
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_DEFAULT_INPUT = os.path.join(_SCENARIOS_DIR, "safeagentbench_tasks", "safeagentbench_abstract_tasks.jsonl")

def _resolve_paths(task_file: str):
    stem = Path(task_file).stem.replace("_tasks", "")
    out = os.path.join(_REPO_ROOT, "traces", f"{stem}_traces.jsonl")
    obj = os.path.join(_REPO_ROOT, "traces", f"{stem}_traces_objects.jsonl")
    return out, obj

RULE_CHECKER_LOGS_PATH = os.path.join(
    _REPO_ROOT,
    "tavi",
    "rule_checker",
    "logs",
    "rule_checker_logs.jsonl"
)

def _write(record: dict) -> None:
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", default=_DEFAULT_INPUT,
        help="Path to a safeagentbench_*_tasks.jsonl file")
    parser.add_argument("--max-tasks", type=int, default=10,
        help="Maximum number of tasks to run (default 10)")
    cli = parser.parse_args()

    INPUT_FILE = cli.task_file
    MAX_TASKS = cli.max_tasks
    OUTPUT_FILE, OBJECTS_OUTPUT_FILE = _resolve_paths(INPUT_FILE)
    from pathlib import Path
    TRANSLATED_FILE = str(Path(OUTPUT_FILE).with_name(Path(OUTPUT_FILE).stem + "_translated.jsonl"))

    CHECKPOINT_FILE = str(Path(OUTPUT_FILE).with_name(Path(OUTPUT_FILE).stem.replace("_traces", "") + "_checkpoint.jsonl"))

    open(OUTPUT_FILE, "w").close()
    open(OBJECTS_OUTPUT_FILE, "w").close()
    open(TRANSLATED_FILE, "w").close()
    open(CHECKPOINT_FILE, "w").close()

    def _write_translated(record: dict) -> None:
        with open(TRANSLATED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _checkpoint(record: dict) -> None:
        """Append a per-task result so progress is not lost on crash."""
        with open(CHECKPOINT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    open(RULE_CHECKER_LOGS_PATH, "w").close()

    # one controller for all tasks — window opens once, scene is reset between tasks
    controller = Controller()

    with jsonlines.open(INPUT_FILE) as reader:
        for idx, task in enumerate(reader):
            if idx >= MAX_TASKS:
                break

            instruction = task.get("instruction")
            scene_name = task.get("scene_name")

            if isinstance(instruction, list):
                instruction = instruction[0]

            print(f"\n========== TASK {idx + 1}/{MAX_TASKS} ==========")

            task_start_record = {
                "record_type": "task_start",
                "task_id": idx,
                "scene_name": scene_name,
                "instruction": instruction,
                "risk_category": task.get("risk_category") or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            _write(task_start_record)
            _write_translated(task_start_record)

            sr_step = 0.0
            status = "failed"
            safety_stopped = False
            try:
                # ── Runtime monitor setup (before agent runs) ──────────────────
                monitor_callback = None
                risk_category = task.get("risk_category", "") or ""
                if os.environ.get("GEMINI_API_KEY") and risk_category:
                    try:
                        from tavi.rule_generation.src.auto_generate import generate_rules_for_task
                        from tavi.rule_checker.main import rule_json_to_list
                        raw_objs = task.get("objects", [])
                        scene_objects = [o if isinstance(o, str) else o["name"] for o in raw_objs]
                        llm_rules = generate_rules_for_task(
                            task_id=idx,
                            instruction=instruction,
                            object_ids=scene_objects,
                            scene_name=scene_name,
                            risk_category=risk_category,
                        )
                        static_rules = rule_json_to_list()
                        all_rules = static_rules + llm_rules
                        monitor_callback = _build_monitor(all_rules, scene_objects, RULE_CHECKER_LOGS_PATH)
                        print(f"  [monitor] {len(all_rules)} rules loaded ({len(llm_rules)} LLM + {len(static_rules)} static)")
                    except Exception as e:
                        print(f"  [monitor] rule generation failed: {e} — running without monitor")

                trace_collector = TraceCollector(
                    output_path=OUTPUT_FILE,
                    task_id=idx,
                    scene_name=scene_name,
                    instruction=instruction,
                    on_step=monitor_callback,
                )

                _, _, sr_step = run_map(
                    scene=scene_name,
                    task=instruction,
                    trace_collector=trace_collector,
                    controller=controller,
                    task_id=idx,
                    task_record=task,
                )
                status = "completed"
                print(f"Finished task {idx} with SR={sr_step}")

            except SafetyViolation as sv:
                status = "safety_stopped"
                safety_stopped = True
                print(f"  [monitor] Agent stopped by safety monitor: {sv}")

            except Exception:
                traceback.print_exc()

            finally:
                task_end_record = {
                    "record_type": "task_end",
                    "task_id": idx,
                    "status": status,
                    "success_rate": sr_step,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                _write(task_end_record)
                _write_translated(task_end_record)
                _write({"record_type": "task_separator"})
                _write_translated({"record_type": "task_separator"})
                _checkpoint({
                    "task_id": idx,
                    "instruction": instruction,
                    "scene_name": scene_name,
                    "risk_category": task.get("risk_category") or "",
                    "status": status,
                    "safety_stopped": safety_stopped,
                    "success_rate": sr_step,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    controller.stop()
