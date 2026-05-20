import json
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

_SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "simulation", "scenarios")
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_FILE = os.path.join(_SCENARIOS_DIR, "safeagentbench_tasks", "safeagentbench_long_horizon_tasks.jsonl")

# Output trace mirrors the input name: safeagentbench_abstract_tasks → safeagentbench_abstract_traces
_input_stem = Path(INPUT_FILE).stem.replace("_tasks", "")
OUTPUT_FILE = os.path.join(_REPO_ROOT, "traces", f"{_input_stem}_traces.jsonl")


def _write(record: dict) -> None:
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    open(OUTPUT_FILE, "w").close()

    # one controller for all tasks — window opens once, scene is reset between tasks
    controller = Controller()

    MAX_TASKS = 10

    sr_scores = []

    with jsonlines.open(INPUT_FILE) as reader:
        for idx, task in enumerate(reader):
            if idx >= MAX_TASKS:
                break

            instruction = task.get("instruction")
            scene_name = task.get("scene_name")

            if isinstance(instruction, list):
                instruction = instruction[0]

            print(f"\n========== TASK {idx + 1}/{MAX_TASKS} ==========")

            _write({
                "record_type": "task_start",
                "task_id": idx,
                "scene_name": scene_name,
                "instruction": instruction,
                "risk_category": task.get("risk_category", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            sr_step = 0.0
            status = "failed"
            try:
                trace_collector = TraceCollector(
                    output_path=OUTPUT_FILE,
                    task_id=idx,
                    scene_name=scene_name,
                    instruction=instruction,
                )

                _, _, sr_step = run_map(
                    scene=scene_name,
                    task=instruction,
                    trace_collector=trace_collector,
                    controller=controller,
                )
                status = "completed"
                print(f"Finished task {idx} with SR={sr_step:.2f}")

            except Exception:
                traceback.print_exc()

            finally:
                sr_scores.append(sr_step)
                _write({
                    "record_type": "task_end",
                    "task_id": idx,
                    "status": status,
                    "success_rate": sr_step,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                _write({"record_type": "task_separator"})

    controller.stop()

    avg_sr = sum(sr_scores) / len(sr_scores) if sr_scores else 0.0
    print(f"\n========== RESULTS ==========")
    print(f"Tasks run : {len(sr_scores)}")
    for i, sr in enumerate(sr_scores):
        print(f"  Task {i:02d}: SR={sr:.2f}")
    print(f"Average SR: {avg_sr:.4f}")
