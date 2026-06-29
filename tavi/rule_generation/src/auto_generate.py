"""
End-to-end per-task rule generation pipeline.

Calls the two-step Bogdan pipeline:
  1. instruction + scene objects -> plain-English rules (Gemini)
  2. plain-English rules -> LTL templates (Gemini)

Results are cached under rule_generation/outputs/task_rules/<task_id>/
so Gemini is called only once per task.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_RULE_GENERATION_ROOT = Path(__file__).resolve().parents[2]
_TASK_CACHE_DIR = _RULE_GENERATION_ROOT / "outputs" / "task_rules"


def _cache_path(task_id: int) -> Path:
    return _TASK_CACHE_DIR / str(task_id) / "rules_ltl_templates.json"


def generate_rules_for_task(
    task_id: int,
    instruction: str,
    object_ids: list[str],
    scene_name: str = "",
    force: bool = False,
) -> list[dict[str, Any]]:
    """
    Generate LTL template rules for a single task via the LLM pipeline.

    Returns the list of rule dicts (same schema as rules_ltl_templates.json).
    Uses a file cache — skips Gemini if rules already exist for this task_id.

    Raises RuntimeError if GEMINI_API_KEY is not set.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to .env to enable automatic rule generation."
        )

    cached = _cache_path(task_id)
    if cached.exists() and not force:
        return json.loads(cached.read_text(encoding="utf-8"))

    from .plain_english.main_english_rule_generator import generate_rules_for_mission
    from .ltl.main_ltl_template_generation import generate_ltl_templates_for_rules

    task_output_dir = _TASK_CACHE_DIR / str(task_id)
    task_output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1 — instruction → plain-English rules
    run_dir = generate_rules_for_mission(
        mission_instruction=instruction,
        high_level_plan="",
        low_level_plan=[],
        scene_objects=object_ids,
        env_info=f"AI2-THOR scene: {scene_name}" if scene_name else "",
        output_dir=task_output_dir,
        debug_output=False,
        revision_rounds=1,
    )

    plain_english_path = run_dir / "plain_english_rules.json"
    if not plain_english_path.exists():
        raise RuntimeError(f"Rule generation produced no plain_english_rules.json under {run_dir}")

    # Step 2 — plain-English rules → LTL templates
    generate_ltl_templates_for_rules(
        plain_english_rules_path=plain_english_path,
        output_dir=task_output_dir,
        model="gemini-2.5-flash",
        temperature=0.2,
    )

    # main_ltl_template_generation always writes final output to outputs/rules_ltl_templates.json
    # but also to config.accepted_templates_path inside task_output_dir. Find it.
    candidates = list(task_output_dir.rglob("accepted_ltl_templates.json"))
    if not candidates:
        # fall back to the global output file
        fallback = _RULE_GENERATION_ROOT / "outputs" / "rules_ltl_templates.json"
        if fallback.exists():
            rules = json.loads(fallback.read_text(encoding="utf-8"))
        else:
            rules = []
    else:
        rules = json.loads(candidates[0].read_text(encoding="utf-8"))

    cached.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
    return rules
