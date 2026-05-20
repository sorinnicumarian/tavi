"""
Model benchmark — runs N tasks per category per model, saves results to CSV.

Usage:
    python benchmark.py

Output:
    benchmark_results/benchmark_<timestamp>.csv
"""

import csv
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import jsonlines
from dotenv import load_dotenv
from ai2thor.controller import Controller

load_dotenv()

MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]
MAX_TASKS = 10

_REPO_ROOT = Path(__file__).parent
_TASKS_DIR = _REPO_ROOT / "tavi/simulation/scenarios/safeagentbench_tasks"

CATEGORIES = {
    "abstract":     _TASKS_DIR / "safeagentbench_abstract_tasks.jsonl",
    "long_horizon": _TASKS_DIR / "safeagentbench_long_horizon_tasks.jsonl",
}

RESULTS_DIR = _REPO_ROOT / "benchmark_results"
RESULTS_DIR.mkdir(exist_ok=True)


def _max_tokens_for(model: str) -> int:
    return 16000


def _safe_response_text(response) -> str:
    if response.text is not None:
        return response.text.strip()
    try:
        parts = response.candidates[0].content.parts
        text = " ".join(
            p.text for p in parts
            if getattr(p, "thought", False) is False and p.text
        ).strip()
        return text if text else parts[-1].text.strip()
    except Exception:
        return ""


def _patch_model(model: str) -> None:
    import tavi.simulation.planner.map_vlm as map_vlm
    import tavi.simulation.planner.utils as utils_mod

    map_vlm.GEMINI_MODEL = model

    def _call_gemini_patched(m, prompt, system_prompt="You are a helpful assistant.", temperature=0.2, max_tokens=1024):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{prompt}"
        effective_max_tokens = 16000
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=effective_max_tokens,
            )
        )
        return _safe_response_text(response)

    utils_mod.call_gpt = _call_gemini_patched

    def _ask_gemini_patched(self, prompt, image_base64=None):
        from google.genai import types
        import base64
        contents = []
        if image_base64 is not None:
            image_bytes = base64.b64decode(image_base64)
            contents = [prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/png")]
        else:
            contents = [prompt]
        effective_max_tokens = 16000
        response = map_vlm.client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=effective_max_tokens),
        )
        return _safe_response_text(response)

    map_vlm.Agents.ask_gemini = _ask_gemini_patched


def run_benchmark(model: str, category: str, input_file: Path, controller: Controller) -> dict:
    from tavi.simulation.planner.map_vlm import run_map

    _patch_model(model)

    tasks_run = []
    with jsonlines.open(input_file) as reader:
        for idx, task in enumerate(reader):
            if idx >= MAX_TASKS:
                break

            instruction = task.get("instruction")
            scene_name = task.get("scene_name")
            if isinstance(instruction, list):
                instruction = instruction[0]

            print(f"\n  [{model}|{category}] Task {idx + 1}/{MAX_TASKS}: {instruction[:60]}…")

            sr = 0.0
            status = "failed"
            try:
                _, _, sr = run_map(
                    scene=scene_name,
                    task=instruction,
                    controller=controller,
                )
                status = "completed"
            except Exception:
                traceback.print_exc()

            tasks_run.append({
                "task_id": idx + 1,
                "category": category,
                "source_file": input_file.name,
                "scene_name": scene_name,
                "instruction": instruction,
                "status": status,
                "success_rate": sr,
            })
            print(f"  SR={sr:.2f}")

    avg_sr = sum(t["success_rate"] for t in tasks_run) / len(tasks_run) if tasks_run else 0.0
    return {"model": model, "category": category, "avg_sr": avg_sr, "tasks": tasks_run}


if __name__ == "__main__":
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # collect all results: list of {model, category, avg_sr, tasks}
    all_results = []

    controller = Controller()

    for category, input_file in CATEGORIES.items():
        for model in MODELS:
            print(f"\n{'='*60}")
            print(f"  MODEL: {model}  |  CATEGORY: {category}")
            print(f"{'='*60}")
            result = run_benchmark(model, category, input_file, controller)
            all_results.append(result)
            print(f"\n  ✓ [{category}] {model}  avg SR = {result['avg_sr']:.4f}")

    controller.stop()

    # ── save CSV ───────────────────────────────────────────────────────────
    csv_path = RESULTS_DIR / f"benchmark_{timestamp}.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)

        # metadata block
        writer.writerow(["run_timestamp", timestamp])
        writer.writerow(["max_tasks_per_category", MAX_TASKS])
        writer.writerow(["categories", ", ".join(CATEGORIES.keys())])
        for model in MODELS:
            writer.writerow([model, f"max_output_tokens={_max_tokens_for(model)}"])
        writer.writerow([])

        # per-task results
        writer.writerow(["task_id", "category", "source_file", "scene", "instruction"] + MODELS)
        for category in CATEGORIES:
            cat_results = {r["model"]: r for r in all_results if r["category"] == category}
            ref_tasks = cat_results[MODELS[0]]["tasks"]
            for i, ref_task in enumerate(ref_tasks):
                srs = []
                for model in MODELS:
                    tasks = cat_results[model]["tasks"]
                    srs.append(f"{tasks[i]['success_rate']:.2f}" if i < len(tasks) else "")
                writer.writerow([
                    ref_task["task_id"],
                    category,
                    ref_task["source_file"],
                    ref_task["scene_name"],
                    ref_task["instruction"],
                ] + srs)
            # per-category average row
            writer.writerow([
                "AVERAGE", category, "", "", "",
            ] + [f"{cat_results[m]['avg_sr']:.4f}" for m in MODELS])
            writer.writerow([])

        # overall average
        for model in MODELS:
            model_results = [r for r in all_results if r["model"] == model]
            overall = sum(r["avg_sr"] for r in model_results) / len(model_results)
            writer.writerow(["OVERALL_AVERAGE", "", "", "", model] + [f"{overall:.4f}"])

    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print("="*60)
    for category in CATEGORIES:
        print(f"\n  Category: {category}")
        for model in MODELS:
            r = next(x for x in all_results if x["model"] == model and x["category"] == category)
            print(f"    {model:30s}  avg SR = {r['avg_sr']:.4f}")
    print(f"\nSaved to: {csv_path}")
