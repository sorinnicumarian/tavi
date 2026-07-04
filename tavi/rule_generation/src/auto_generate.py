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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any

TASK_TIMEOUT_SECONDS = 90

_RULE_GENERATION_ROOT = Path(__file__).resolve().parents[1]  # .../rule_generation/
_TASK_CACHE_DIR = _RULE_GENERATION_ROOT / "outputs" / "task_rules"


def _cache_path(task_id: int, instruction: str = "") -> Path:
    # Include a short hash of the instruction so parallel runs on different files
    # with the same task_id index don't share a cache entry.
    import hashlib
    suffix = "_" + hashlib.md5(instruction.encode()).hexdigest()[:8] if instruction else ""
    return _TASK_CACHE_DIR / f"{task_id}{suffix}" / "rules_ltl_templates.json"



def _load_nonexistent_predicates() -> "re.Pattern":
    """Load the list of non-existent predicates from context/repair_rules.md."""
    import re
    repair_md = _RULE_GENERATION_ROOT / "context" / "repair_rules.md"
    predicates = []
    if repair_md.exists():
        in_block = False
        for line in repair_md.read_text(encoding="utf-8").splitlines():
            if line.strip() == "```" and not in_block:
                in_block = True
                continue
            if line.strip() == "```" and in_block:
                break
            if in_block and line.strip():
                predicates.append(re.escape(line.strip()))
    if not predicates:
        raise RuntimeError(f"No non-existent predicates found in {repair_md}")
    return re.compile(r"\b(" + "|".join(predicates) + r")")


def _repair_rules(rules: list[dict]) -> list[dict]:
    """
    Post-processing repair: fix LLM formulas that reference non-existent predicates.
    The list of bad predicates and canonical replacements is loaded from
    context/repair_rules.md — edit that file to add new cases.
    """
    import re

    _NONEXISTENT = _load_nonexistent_predicates()

    repaired = []
    for rule in rules:
        if rule.get("status") == "not_expressible_with_current_trace_predicates":
            repaired.append(rule)
            continue

        formula = rule.get("formula_template", "")
        if not formula:
            repaired.append(rule)
            continue

        # Fix 3-arg filled_with_liquid (e.g. filled_with_liquid__{c}__water)
        formula = re.sub(r"filled_with_liquid__(\{[^}]+\})__\w+", r"filled_with_liquid__\1", formula)
        formula = re.sub(r"filled_with_liquid__([a-z_0-9]+)__\w+", r"filled_with_liquid__\1", formula)

        # If formula still uses a non-existent predicate, rewrite or mark not_expressible
        if _NONEXISTENT.search(formula):
            # Attempt: replace broken__{x} pattern with the canonical drop-detection formula
            if "broken__" in formula:
                # Extract the object variable from broken__{x}
                m = re.search(r"broken__(\{[^}]+\}|[a-z_0-9]+)", formula)
                var = m.group(1) if m else "{x}"
                rule = dict(rule)
                rule["formula_template"] = (
                    f"G(!(exec__drophandobject & removed__holding__{var} & fragile__{var}))"
                )
                rule["_repaired"] = "replaced broken__ with drop-detection pattern"
                repaired.append(rule)
            else:
                rule = dict(rule)
                rule["status"] = "not_expressible_with_current_trace_predicates"
                rule["_repaired"] = "contains non-existent predicate"
                repaired.append(rule)
        else:
            rule = dict(rule, formula_template=formula)
            repaired.append(rule)

    return repaired


def _generate_rules_inner(
    task_id, instruction, object_ids, scene_name, risk_category=""
):
    """Actual generation logic — runs inside a thread for timeout enforcement."""
    from .plain_english.main_english_rule_generator import generate_rules_for_mission
    from .ltl.main_ltl_template_generation import generate_ltl_templates_for_rules

    task_output_dir = _TASK_CACHE_DIR / str(task_id)
    task_output_dir.mkdir(parents=True, exist_ok=True)

    env_parts = [f"AI2-THOR scene: {scene_name}" if scene_name else ""]
    if risk_category:
        env_parts.append(f"KNOWN RISK CATEGORY FOR THIS TASK: {risk_category}")
        env_parts.append(
            "Focus your rules on detecting this specific hazard type. "
            "Write at least one LTL rule that directly targets this risk category."
        )
    env_info = "\n\n".join(p for p in env_parts if p)

    run_dir = generate_rules_for_mission(
        mission_instruction=instruction,
        high_level_plan="",
        low_level_plan=[],
        scene_objects=object_ids,
        env_info=env_info,
        output_dir=task_output_dir,
        debug_output=False,
        revision_rounds=0,
        model="gemini-2.5-flash",
    )

    plain_english_path = run_dir / "plain_english_rules.json"
    if not plain_english_path.exists():
        raise RuntimeError(f"No plain_english_rules.json under {run_dir}")

    generate_ltl_templates_for_rules(
        plain_english_rules_path=plain_english_path,
        output_dir=task_output_dir,
        model="gemini-2.5-flash",
        temperature=0.2,
    )

    candidates = list(task_output_dir.rglob("accepted_ltl_templates.json"))
    if candidates:
        rules = json.loads(candidates[0].read_text(encoding="utf-8"))
    else:
        fallback = _RULE_GENERATION_ROOT / "outputs" / "rules_ltl_templates.json"
        rules = json.loads(fallback.read_text(encoding="utf-8")) if fallback.exists() else []

    rules = _repair_rules(rules)

    cached = _cache_path(task_id, instruction)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
    return rules


def generate_rules_for_task(
    task_id: int,
    instruction: str,
    object_ids: list[str],
    scene_name: str = "",
    risk_category: str = "",
    force: bool = False,
) -> list[dict[str, Any]]:
    """
    Generate LTL template rules for a single task via the LLM pipeline.

    Rules are generated from instruction + scene objects only — no trace access.
    This supports true runtime monitoring: rules are ready before the agent runs.

    Uses gemini-2.5-flash with no revision rounds for speed.
    Times out after TASK_TIMEOUT_SECONDS and raises RuntimeError.
    Results are cached — Gemini is only called once per task_id.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY not set")

    cached = _cache_path(task_id, instruction)
    if cached.exists() and not force:
        result = json.loads(cached.read_text(encoding="utf-8"))
        return result if result is not None else []

    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(
            _generate_rules_inner,
            task_id, instruction, object_ids, scene_name, risk_category,
        )
        try:
            return future.result(timeout=TASK_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            raise RuntimeError(
                f"Task {task_id} rule generation timed out after {TASK_TIMEOUT_SECONDS}s"
            )
