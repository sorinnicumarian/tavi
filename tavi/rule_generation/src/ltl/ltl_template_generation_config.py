"""
Configuration utilities for the LTL-template generation stage.

Main responsibility:
- load the LTL-template prompt
- load plain-English rule inputs
- normalize rule dictionaries into the format expected by the prompt
- render one prompt per rule
- provide output paths for accepted/rejected/raw LTL-template outputs

"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


@dataclass
class LTLTemplateGenerationConfig:
    """
    Configuration object for the plain-English-rule -> LTL-template stage.

    Parameters
    ----------
    project_root:
        Root folder of the rule_generation project.
    prompt_path:
        Path to prompts/plain_english_to_ltl_template_prompt.md.
    schema_path:
        Path to schemas/ltl_template_rule.schema.json.
    input_rules_path:
        Path to the JSON file containing plain-English rules.
        For early testing, this can point to test_cases/plain_english_ltl_template_test_cases.json.
    output_dir:
        Directory where LTL-template generation outputs will be written.
    """

    project_root: Path
    prompt_path: Path
    schema_path: Path
    input_rules_path: Path
    output_dir: Path

    # The placeholder used inside plain_english_to_ltl_template_prompt.md
    prompt_rule_placeholder: str = "{{PLAIN_ENGLISH_RULE_JSON}}"

    @classmethod
    def from_project_root(
        cls,
        project_root: Path | str = ".",
        input_rules_path: Optional[Path | str] = None,
        output_dir: Optional[Path | str] = None,
    ) -> "LTLTemplateGenerationConfig":
        """
        Build a default config from the rule_generation project root.

        By default, input_rules_path points to:
            outputs/plain_english_rules.json

        During prompt testing, pass:
            test_cases/plain_english_ltl_template_test_cases.json
        """

        root = Path(project_root).resolve()

        return cls(
            project_root=root,
            prompt_path=root / "prompts" / "plain_english_to_ltl_template_prompt.md",
            schema_path=root / "schemas" / "ltl_template_rule.schema.json",
            input_rules_path=(
                root / input_rules_path
                if input_rules_path is not None and not Path(input_rules_path).is_absolute()
                else Path(input_rules_path).resolve()
                if input_rules_path is not None
                else root / "outputs" / "plain_english_rules.json"
            ),
            output_dir=(
                root / output_dir
                if output_dir is not None and not Path(output_dir).is_absolute()
                else Path(output_dir).resolve()
                if output_dir is not None
                else root / "outputs" / "ltl_templates"
            ),
        )

    def load_schema(self) -> JsonDict:
        """Load the JSON schema used to validate LTL-template outputs."""

        with self.schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def load_input_rules(self) -> List[JsonDict]:
        """
        Load and normalize input plain-English rules.

        Supported input shapes
        ----------------------

        1. List of rule dictionaries:
            [
              {"rule_id": "R01", "plain_english_rule": "..."},
              ...
            ]

        2. Dictionary of rule dictionaries:
            {
              "Rule R01: Some Title": {
                "Plain-English rule": "...",
                ...
              }
            }

        3. Test-case wrapper:
            {
              "purpose": "...",
              "test_cases": [
                {"rule_id": "T01", "plain_english_rule": "..."},
                ...
              ]
            }

        Returns
        -------
        list[dict]
            Normalized rule dictionaries with stable keys:
            - rule_id
            - title
            - hazard_types
            - plain_english_rule
            - pattern_family
        """

        with self.input_rules_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        raw_rules = self._extract_rule_list(raw_data)
        return [self.normalize_rule(rule, fallback_index=i) for i, rule in enumerate(raw_rules, start=1)]

    def _extract_rule_list(self, raw_data: Any) -> List[JsonDict]:
        """
        Extract a list of rule dictionaries from several possible JSON shapes.
        """

        if isinstance(raw_data, list):
            return raw_data

        if isinstance(raw_data, dict) and isinstance(raw_data.get("test_cases"), list):
            return raw_data["test_cases"]

        if isinstance(raw_data, dict):
            extracted: List[JsonDict] = []

            for key, value in raw_data.items():
                if not isinstance(value, dict):
                    continue

                rule = dict(value)
                rule.setdefault("_source_key", key)
                extracted.append(rule)

            if extracted:
                return extracted

        raise ValueError(
            "Unsupported input rules JSON format. Expected a list, a dictionary of rules, "
            "or a wrapper containing a 'test_cases' list."
        )

    # ------------------------------------------------------------------
    # Rule normalization
    # ------------------------------------------------------------------

    def normalize_rule(self, rule: JsonDict, fallback_index: int) -> JsonDict:
        """
        Normalize one plain-English rule into the key names expected by the prompt.

        This is intentionally tolerant because earlier generation stages may use
        slightly different names such as:
        - "Plain-English rule"
        - "Hazard types"
        - "Pattern family"
        """

        source_key = str(rule.get("_source_key", ""))

        rule_id = (
            rule.get("rule_id")
            or rule.get("Rule ID")
            or rule.get("id")
            or f"R{fallback_index:03d}"
        )

        title = (
            rule.get("title")
            or rule.get("Title")
            or str(rule_id)
        )

        hazard_types = (
            rule.get("hazard_types")
            or rule.get("Hazard types")
            or rule.get("Hazard Types")
            or rule.get("hazards")
            or []
        )

        if isinstance(hazard_types, str):
            hazard_types = [hazard_types]

        plain_english_rule = (
            rule.get("plain_english_rule")
            or rule.get("Plain-English rule")
            or rule.get("Plain English Rule")
            or rule.get("rule")
            or rule.get("Rule")
        )

        if not plain_english_rule:
            raise ValueError(f"Rule {rule_id} is missing a plain-English rule text.")

        pattern_family = (
            rule.get("pattern_family")
            or rule.get("Pattern family")
            or rule.get("Pattern Family")
            or rule.get("expected_pattern_family")
            or "Unspecified"
        )

        normalized: JsonDict = {
            "rule_id": str(rule_id),
            "title": str(title),
            "hazard_types": list(hazard_types),
            "plain_english_rule": str(plain_english_rule),
            "pattern_family": str(pattern_family),
        }

        # Preserve useful optional fields for testing/debugging.
        optional_passthrough_keys = [
            "expected_status",
            "expected_key_predicates",
            "expected_missing_concepts",
            "test_focus",
            "why_it_matters",
            "Why it matters",
            "key_trace_concepts",
            "Key trace concepts",
        ]

        for key in optional_passthrough_keys:
            if key in rule:
                normalized[key] = rule[key]

        return normalized

    # ------------------------------------------------------------------
    # Prompt rendering
    # ------------------------------------------------------------------

    def render_prompt(self, rule: JsonDict, prompt_template: Optional[str] = None) -> str:
        """
        Render the prompt for one normalized plain-English rule.

        Parameters
        ----------
        rule:
            One normalized rule dictionary.
        prompt_template:
            Optional already-loaded prompt template. If omitted, the prompt is loaded
            from disk.

        Returns
        -------
        str
            Complete prompt ready to send to the LLM.
        """

        if prompt_template is None:
            prompt_template = self.prompt_path.read_text(encoding="utf-8")

        normalized_rule = self.normalize_rule(rule, fallback_index=1)

        rule_json = json.dumps(normalized_rule, indent=2, ensure_ascii=False)

        if self.prompt_rule_placeholder not in prompt_template:
            raise ValueError(
                f"Prompt placeholder {self.prompt_rule_placeholder!r} not found in "
                f"{self.prompt_path}."
            )

        return prompt_template.replace(self.prompt_rule_placeholder, rule_json)

    def render_all_prompts(self) -> List[JsonDict]:
        """
        Render prompts for all input rules.

        Returns
        -------
        list[dict]
            Each item contains:
            - rule_id
            - rule
            - prompt
        """

        prompt_template = self.prompt_path.read_text(encoding="utf-8")
        rules = self.load_input_rules()

        rendered = []
        for rule in rules:
            rendered.append(
                {
                    "rule_id": rule["rule_id"],
                    "rule": rule,
                    "prompt": self.render_prompt(rule, prompt_template),
                }
            )

        return rendered

    # ------------------------------------------------------------------
    # Output paths
    # ------------------------------------------------------------------

    @property
    def accepted_templates_path(self) -> Path:
        return self.output_dir / "rules_ltl_templates.json"

    @property
    def rejected_templates_path(self) -> Path:
        return self.output_dir / "rejected_rules.json"

    @property
    def raw_outputs_path(self) -> Path:
        return self.output_dir / "raw_llm_outputs.json"

    @property
    def run_summary_path(self) -> Path:
        return self.output_dir / "run_summary.json"

    def output_paths(self) -> JsonDict:
        """
        Return all standard output paths as strings.
        Useful for logging/debugging.
        """

        return {
            "accepted_templates": str(self.accepted_templates_path),
            "rejected_templates": str(self.rejected_templates_path),
            "raw_outputs": str(self.raw_outputs_path),
            "run_summary": str(self.run_summary_path),
        }


def save_json(path: Path, data: Any) -> None:
    """
    Save JSON data with stable formatting.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    # Lightweight manual sanity check.
    config = LTLTemplateGenerationConfig.from_project_root(
        project_root=".",
        input_rules_path="test_cases/plain_english_ltl_template_test_cases.json",
    )

    config.validate_paths()
    config.ensure_output_dir()

    rules = config.load_input_rules()
    prompts = config.render_all_prompts()

    print(f"Loaded {len(rules)} rule(s).")
    print(f"Rendered {len(prompts)} prompt(s).")
    print("Output paths:")
    for label, path in config.output_paths().items():
        print(f"  {label}: {path}")
