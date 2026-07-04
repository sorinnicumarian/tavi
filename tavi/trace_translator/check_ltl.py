from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ground_rules import GroundedRule, ground_all_rules
from load_traces import TaskTrace, load_traces
from rule_templates import default_rule_templates


@dataclass(frozen=True)
class CheckResult:
    """Result of checking one grounded LTL formula on one task trace."""

    task_id: int | str
    instruction: str
    risk_category: str
    rule_id: str
    description: str
    binding: dict[str, str]
    formula: str
    satisfied: bool


def _get_ltlf_parser():
    """
    Import flloat only when checking formulas.

    Install dependency:
        pip install flloat
    """
    try:
        from flloat.parser.ltlf import LTLfParser
    except ImportError as exc:
        raise ImportError(
            "flloat is not installed. Install it with: pip install flloat"
        ) from exc

    return LTLfParser()


def check_grounded_rule(
    task: TaskTrace,
    grounded_rule: GroundedRule,
) -> CheckResult:
    """Parse and check one grounded LTLf rule on one task trace."""
    parser = _get_ltlf_parser()
    parsed_formula = parser(grounded_rule.formula)

    # flloat expects:
    #   list[dict[atom_name, bool]]
    # and checks from position 0 by default.
    satisfied = bool(parsed_formula.truth(task.steps, 0))

    return CheckResult(
        task_id=task.task_id,
        instruction=task.instruction,
        risk_category=task.risk_category,
        rule_id=grounded_rule.rule_id,
        description=grounded_rule.description,
        binding=grounded_rule.binding,
        formula=grounded_rule.formula,
        satisfied=satisfied,
    )


def check_task(task: TaskTrace) -> list[CheckResult]:
    """Ground default templates on one task, then check all resulting formulas."""
    templates = default_rule_templates()
    grounded_rules = ground_all_rules(task.steps, templates)

    return [
        check_grounded_rule(task, grounded_rule)
        for grounded_rule in grounded_rules
    ]


def check_trace_file(path: str | Path) -> list[CheckResult]:
    """Load a translated trace file and check all tasks."""
    tasks = load_traces(path)

    results: list[CheckResult] = []
    for task in tasks:
        results.extend(check_task(task))

    return results


def print_results(results: list[CheckResult]) -> None:
    """Small console report."""
    if not results:
        print("No grounded rules were generated.")
        return

    failed = [result for result in results if not result.satisfied]

    print(f"Checked {len(results)} grounded formulas")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")

    for result in failed:
        print()
        print(f"Task {result.task_id} | {result.risk_category}")
        print(f"Instruction: {result.instruction}")
        print(f"FAILED {result.rule_id} | binding={result.binding}")
        print(result.formula)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Offline LTLf checker for translated TAVI traces."
    )
    parser.add_argument("trace_file", help="Path to translated JSONL trace file")
    args = parser.parse_args()

    all_results = check_trace_file(args.trace_file)
    print_results(all_results)