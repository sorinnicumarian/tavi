"""
Runner for the LTL-template generation stage.

This script takes plain-English safety rules and translates each one into a
parametric LTL-template JSON object.

"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


from ltl_template_generation_config import (
    LTLTemplateGenerationConfig,
    save_json,
)
from ltl_template_translator_agent import LTLTemplateTranslatorAgent
from ltl_template_validator import LTLTemplateValidator


JsonDict = Dict[str, Any]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate parametric LTL templates from plain-English safety rules."
    )

    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Path to the rule_generation project root. Default: current directory.",
    )

    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "Path to plain-English rules JSON file. "
            "Default: outputs/plain_english_rules.json"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directory for LTL-template outputs. "
            "Default: outputs/ltl_templates"
        ),
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-pro",
        help="Gemini model name.",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Gemini temperature for LTL-template generation.",
    )

    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=8192,
        help="Maximum Gemini output tokens.",
    )

    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=1024,
        help="Gemini thinking budget.",
    )

    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    config = LTLTemplateGenerationConfig.from_project_root(
        project_root=args.project_root,
        input_rules_path=args.input,
        output_dir=args.output_dir,
    )

    config.validate_paths()
    config.ensure_output_dir()

    rendered_prompts = config.render_all_prompts()

    agent = LTLTemplateTranslatorAgent(
        model=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        thinking_budget=args.thinking_budget,
    )

    validator = LTLTemplateValidator(config.schema_path)

    accepted: List[JsonDict] = []
    rejected: List[JsonDict] = []
    raw_outputs: List[JsonDict] = []

    print(f"Loaded {len(rendered_prompts)} plain-English rule(s).")
    print("Starting LTL-template generation...")

    for index, item in enumerate(rendered_prompts, start=1):
        rule_id = item["rule_id"]
        source_rule = item["rule"]
        prompt = item["prompt"]

        print(f"\n[{index}/{len(rendered_prompts)}] Translating {rule_id}...")

        try:
            generated = agent.translate_rule(prompt)
            raw_text = agent.history[-1] if agent.history else json.dumps(generated)

            raw_outputs.append(
                {
                    "rule_id": rule_id,
                    "source_rule": source_rule,
                    "raw_response": raw_text,
                    "parsed_response": generated,
                }
            )

            errors = validator.validate(generated)

            if errors:
                print(f"{rule_id}: rejected ({len(errors)} validation error(s))")
                rejected.append(
                    {
                        "rule_id": rule_id,
                        "source_rule": source_rule,
                        "generated_template": generated,
                        "errors": errors,
                    }
                )
            else:
                print(f"{rule_id}: accepted")
                accepted.append(generated)

        except Exception as exc:
            print(f"{rule_id}: failed with exception: {exc}")

            raw_outputs.append(
                {
                    "rule_id": rule_id,
                    "source_rule": source_rule,
                    "raw_response": agent.history[-1] if agent.history else None,
                    "exception": repr(exc),
                }
            )

            rejected.append(
                {
                    "rule_id": rule_id,
                    "source_rule": source_rule,
                    "generated_template": None,
                    "errors": [str(exc)],
                }
            )

    summary: JsonDict = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "input_rules_path": str(config.input_rules_path),
        "prompt_path": str(config.prompt_path),
        "schema_path": str(config.schema_path),
        "model": args.model,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "thinking_budget": args.thinking_budget,
        "total_rules": len(rendered_prompts),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "output_paths": config.output_paths(),
    }

    save_json(config.accepted_templates_path, accepted)
    save_json(config.rejected_templates_path, rejected)
    save_json(config.raw_outputs_path, raw_outputs)
    save_json(config.run_summary_path, summary)

    print("\nDone.")
    print(f"Accepted: {len(accepted)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Saved accepted templates to: {config.accepted_templates_path}")
    print(f"Saved rejected rules to: {config.rejected_templates_path}")
    print(f"Saved raw outputs to: {config.raw_outputs_path}")
    print(f"Saved run summary to: {config.run_summary_path}")


if __name__ == "__main__":
    main()
