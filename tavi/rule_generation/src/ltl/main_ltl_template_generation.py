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

from dotenv import load_dotenv

from ltl_template_generation_config import (
    LTLTemplateGenerationConfig,
    save_json,
)
from ltl_template_translator_agent import LTLTemplateTranslatorAgent
from ltl_template_validator import LTLTemplateValidator


JsonDict = Dict[str, Any]

load_dotenv()

def main() -> None:

    config = LTLTemplateGenerationConfig.from_project_root(
        project_root=".",
        input_rules_path="outputs/plain_english_rules.json",
        output_dir="outputs/ltl_templates",
    )

    rendered_prompts = config.render_all_prompts()

    agent = LTLTemplateTranslatorAgent(
        model="gemini-2.5-pro",
        temperature=0.3,
        max_output_tokens=8192,
        thinking_budget=1024,
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
            raw_text = json.dumps(generated)

            raw_outputs.append(
                {
                    "rule_id": rule_id,
                    "source_rule": source_rule,
                    "raw_response": raw_text,
                    "parsed_response": generated,
                }
            )

            # result = validator.validate(generated)

            # if not result.is_valid:
            #     print(f"{rule_id}: rejected ({len(result.errors)} validation error(s))")
            #     rejected.append(
            #         {
            #             "rule_id": rule_id,
            #             "source_rule": source_rule,
            #             "generated_template": generated,
            #             "errors": result.errors,
            #         }
            #     )
            # else:
            print(f"{rule_id}: accepted")
            accepted.append(generated)

        except Exception as exc:
            print(f"{rule_id}: failed with exception: {exc}")

            raw_outputs.append(
                {
                    "rule_id": rule_id,
                    "source_rule": source_rule,
                    "raw_response": json.dumps(generated),
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
        "model": "gemini-2.5-pro",
        "temperature":  0.1,
        "max_output_tokens": 8192,
        "thinking_budget": 1024,
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
