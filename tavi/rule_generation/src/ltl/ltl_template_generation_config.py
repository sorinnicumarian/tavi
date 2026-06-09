"""
Configuration utilities for the LTL-template generation stage.

Main responsibility:
- load the LTL-template prompt
- load authoritative context files
- load plain-English rule inputs
- normalize rule dictionaries into the format expected by the prompt
- render one prompt per rule
- provide output paths for accepted LTL-template outputs
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


REQUIRED_CONTEXT_FILES = [
    "ai2thor_actions.md",
    "ai2thor_object_states.md",
    "ai2thor_object_types_and_categories.md",
    "hazards_types.md",
    "ltl_patterns.md",
]


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
    context_dir:
        Directory containing authoritative context markdown files.
    """

    project_root: Path
    prompt_path: Path
    schema_path: Path
    input_rules_path: Path
    output_dir: Path
    context_dir: Path

    # Placeholder used inside plain_english_to_ltl_template_prompt.md
    prompt_rule_placeholder: str = "{{PLAIN_ENGLISH_RULE_JSON}}"

    # Optional placeholder used inside plain_english_to_ltl_template_prompt.md.
    # If the placeholder is missing, the context block is appended automatically.
    prompt_context_placeholder: str = "{{AUTHORITATIVE_CONTEXT_FILES}}"

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
            input_rules_path=cls._resolve_project_path(
                root=root,
                path=input_rules_path,
                default=root / "outputs" / "plain_english_rules.json",
            ),
            output_dir=cls._resolve_project_path(
                root=root,
                path=output_dir,
                default=root / "outputs" / "ltl_templates",
            ),
            context_dir=root / "context",
        )

    @staticmethod
    def _resolve_project_path(
        root: Path,
        path: Optional[Path | str],
        default: Path,
    ) -> Path:
        """
        Resolve an optional path relative to the project root.

        If path is None, return default.
        If path is absolute, return it as-is.
        If path is relative, resolve it against root.
        """

        if path is None:
            return default

        candidate = Path(path)

        if candidate.is_absolute():
            return candidate.resolve()

        return (root / candidate).resolve()

    # ------------------------------------------------------------------
    # Context loading
    # ------------------------------------------------------------------

    def load_context_files(self) -> dict[str, str]:
        """
        Load all context files required by the LTL-template translator.

        These files are treated as authoritative project knowledge.
        The LTL prompt should use them instead of duplicating all domain
        information inside one large prompt.
        """

        context_sections: dict[str, str] = {}
        missing_files: list[str] = []

        for filename in REQUIRED_CONTEXT_FILES:
            path = self.context_dir / filename

            if not path.exists():
                missing_files.append(str(path))
                continue

            context_sections[filename] = path.read_text(encoding="utf-8")

        if missing_files:
            missing = "\n".join(f"- {p}" for p in missing_files)
            raise FileNotFoundError(
                "Missing required LTL context files:\n"
                f"{missing}\n\n"
                "The LTL-template translator must receive the same authoritative "
                "context modules as the plain-English rule generator."
            )

        return context_sections

    def render_context_block(self) -> str:
        """
        Render context files as clearly separated prompt sections.

        The separators are intentionally explicit so the LLM treats each markdown
        file as a separate source module rather than one blended instruction blob.
        """

        context_sections = self.load_context_files()

        parts = [
            "# Authoritative Context Files",
            "",
            "Use the following context files as the authoritative project knowledge.",
            "Do not invent atoms, predicates, object categories, relations, actions, or future vocabulary outside these files.",
            "If the LTL prompt conflicts with these context files, prefer the context files.",
            "",
        ]

        for filename, content in context_sections.items():
            parts.append(f"<!-- BEGIN CONTEXT FILE: {filename} -->")
            parts.append(f"## `{filename}`")
            parts.append("")
            parts.append(content.strip())
            parts.append("")
            parts.append(f"<!-- END CONTEXT FILE: {filename} -->")
            parts.append("")

        return "\n".join(parts).strip()

    # ------------------------------------------------------------------
    # Schema and input loading
    # ------------------------------------------------------------------

    def load_schema(self) -> JsonDict:
        """Load the JSON schema used to validate LTL-template outputs."""

        with self.schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def load_input_rules(self) -> List[JsonDict]:
        """
        Load and normalize input plain-English rules.

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

        return [
            self.normalize_rule(rule, fallback_index=i)
            for i, rule in enumerate(raw_rules, start=1)
        ]

    def _extract_rule_list(self, raw_data: Any) -> List[JsonDict]:
        """
        Extract a list of rule dictionaries from several possible JSON shapes.
        """

        if isinstance(raw_data, list):
            return raw_data

        if isinstance(raw_data, dict):
            # Support wrappers such as:
            # {"rules": [...]}
            # {"test_cases": [...]}
            for wrapper_key in ("rules", "test_cases"):
                wrapped = raw_data.get(wrapper_key)
                if isinstance(wrapped, list):
                    return wrapped

            # Support dictionary-of-rules format:
            # {"Rule R01: ...": {...}, "Rule R02: ...": {...}}
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
            "or a wrapper containing a 'rules' or 'test_cases' list."
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
            "temporal_diagnostic_structure",
            "Temporal diagnostic structure",
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

        The rendered prompt includes:
        - the base LTL-template prompt,
        - the authoritative context files,
        - the one plain-English rule to translate.

        Parameters
        ----------
        rule:
            One normalized or raw rule dictionary.
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
        context_block = self.render_context_block()

        if self.prompt_rule_placeholder not in prompt_template:
            raise ValueError(
                f"Prompt placeholder {self.prompt_rule_placeholder!r} not found in "
                f"{self.prompt_path}."
            )

        rendered_prompt = prompt_template.replace(
            self.prompt_rule_placeholder,
            rule_json,
        )

        if self.prompt_context_placeholder in rendered_prompt:
            rendered_prompt = rendered_prompt.replace(
                self.prompt_context_placeholder,
                context_block,
            )
        else:
            # Backward-compatible fallback:
            # If the prompt has not yet been refactored to include the context
            # placeholder, append the context block before the input rule section.
            #
            # This still guarantees that the LTL translator receives the context.
            rendered_prompt = (
                rendered_prompt.rstrip()
                + "\n\n---\n\n"
                + context_block
                + "\n"
            )

        return rendered_prompt

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

        rendered: List[JsonDict] = []

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

    def output_paths(self) -> JsonDict:
        """
        Return all standard output paths as strings.
        Useful for logging/debugging.
        """

        return {
            "accepted_templates": str(self.accepted_templates_path),
        }


def save_json(path: Path, data: Any) -> None:
    """
    Save JSON data with stable formatting.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp_path.replace(path)