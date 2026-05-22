"""
Validator for LTL-template rule objects.

This module validates the JSON object produced by the LTL-template translator.

Validation has two layers:

1. JSON Schema validation
   - checks required fields and high-level structure

2. Project-specific validation
   - checks declared variables
   - checks grounding strategies
   - checks forbidden predicates
   - checks that formula predicates belong to the allowed vocabulary

This file does NOT check whether the LTL formula is logically correct.
It only checks whether the template is structurally safe enough for the next
pipeline stage.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple
import jsonschema


JsonDict = Dict[str, Any]


# ----------------------------------------------------------------------
# Allowed vocabulary for the first prototype
# ----------------------------------------------------------------------

ALLOWED_STATE_PREDICATES: Set[str] = {
    "visible",
    "near",
    "holding",
    "open",
    "broken",
    "toggled_on",
    "moving",
}

ALLOWED_PROPERTY_PREDICATES: Set[str] = {
    "pickupable",
    "receptacle",
    "toggleable",
    "openable",
    "breakable",
    "dirtyable",
    "moveable",
    "cookable",
    "sliceable",
    "fillable",
}

ALLOWED_SEMANTIC_PREDICATES: Set[str] = {
    "heat_source",
    "cold_source",
    "fragile",
    "sharp",
    "electrical",
    "flammable",
    "chemical",
    "material",
}

ALLOWED_RELATION_PREDICATES: Set[str] = {
    "on",
    "filled_with_liquid",
}

ALLOWED_BOUNDARY_PREDICATES: Set[str] = {
    "done",
}

ALLOWED_UNARY_PREDICATES: Set[str] = (
    ALLOWED_STATE_PREDICATES
    | ALLOWED_PROPERTY_PREDICATES
    | ALLOWED_SEMANTIC_PREDICATES
)

ALLOWED_PREDICATES: Set[str] = (
    ALLOWED_UNARY_PREDICATES
    | ALLOWED_RELATION_PREDICATES
    | ALLOWED_BOUNDARY_PREDICATES
    | {"exec"}
)

ALLOWED_DELTA_PREFIXES: Set[str] = {
    "added",
    "removed",
}

LTL_OPERATOR_CALLS: Set[str] = {
    "G",
    "F",
    "X",
    "U",
}

FORBIDDEN_PREDICATES: Set[str] = {
    "has_position",
    "distance",
    "agent_position",
    "agent_rotation",
    "unsafe",
    "dangerous",
    "bad_context",
    "incompatible",
    "inside",
    "contains",
}

FORBIDDEN_SUBSTRINGS: Sequence[str] = (
    "has_position(",
    "distance(",
    "agent_position(",
    "agent_rotation(",
    "unsafe(",
    "dangerous(",
    "bad_context(",
    "incompatible(",
    "inside(",
    "contains(",
    "near({",  # binary near often starts like near({x}, {y}); checked more precisely below
)


VARIABLE_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class ValidationResult:
    """Simple validation result container."""

    is_valid: bool
    errors: List[str]


class LTLTemplateValidator:
    """
    Validate LTL-template rule dictionaries.

    Parameters
    ----------
    schema_path:
        Path to schemas/ltl_template_rule.schema.json.
    """

    def __init__(self, schema_path: Path | str):
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema(self.schema_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, rule_template: JsonDict) -> ValidationResult:
        """
        Validate one LTL-template rule object.

        Returns
        -------
        ValidationResult
            is_valid is True when no errors were found.
        """

        errors: List[str] = []

        errors.extend(self._validate_json_schema(rule_template))
        errors.extend(self._validate_status_specific_content(rule_template))

        if rule_template.get("status") == "expressible":
            errors.extend(self._validate_expressible_rule(rule_template))

        return ValidationResult(is_valid=(len(errors) == 0), errors=errors)

    def validate_many(self, rule_templates: Sequence[JsonDict]) -> List[ValidationResult]:
        """Validate multiple rule-template objects."""

        return [self.validate(rule) for rule in rule_templates]

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    @staticmethod
    def _load_schema(schema_path: Path) -> JsonDict:
        with schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_json_schema(self, rule_template: JsonDict) -> List[str]:
        """
        Validate against the JSON Schema.

        Requires the jsonschema package.
        """

        validator = jsonschema.Draft202012Validator(self.schema)

        errors = []
        for error in sorted(validator.iter_errors(rule_template), key=lambda e: list(e.path)):
            path = ".".join(str(part) for part in error.path)
            prefix = f"{path}: " if path else ""
            errors.append(prefix + error.message)

        return errors

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def _validate_status_specific_content(self, rule_template: JsonDict) -> List[str]:
        errors: List[str] = []

        status = rule_template.get("status")

        if status not in {
            "expressible",
            "not_expressible_with_current_trace_predicates",
        }:
            errors.append(
                "Field 'status' must be either 'expressible' or "
                "'not_expressible_with_current_trace_predicates'."
            )

        if status == "not_expressible_with_current_trace_predicates":
            if "formula_template" in rule_template:
                errors.append(
                    "Non-expressible rules must not contain 'formula_template'."
                )
            if "grounding_strategy" in rule_template:
                errors.append(
                    "Non-expressible rules must not contain 'grounding_strategy'."
                )
            if not rule_template.get("reason"):
                errors.append(
                    "Non-expressible rules must include a non-empty 'reason'."
                )
            if not rule_template.get("missing_concepts"):
                errors.append(
                    "Non-expressible rules must include non-empty 'missing_concepts'."
                )

        return errors

    # ------------------------------------------------------------------
    # Expressible rule checks
    # ------------------------------------------------------------------

    def _validate_expressible_rule(self, rule_template: JsonDict) -> List[str]:
        errors: List[str] = []

        formula = rule_template.get("formula_template", "")
        variables = rule_template.get("variables", {})
        grounding_strategy = rule_template.get("grounding_strategy", {})
        required_predicates = rule_template.get("required_predicates", [])

        if not isinstance(formula, str) or not formula.strip():
            errors.append("Expressible rule must contain a non-empty formula_template.")
            return errors

        if not isinstance(variables, dict):
            errors.append("Field 'variables' must be an object.")
            return errors

        if not isinstance(grounding_strategy, dict):
            errors.append("Field 'grounding_strategy' must be an object.")
            return errors

        declared_variables = set(variables.keys())
        formula_variables = extract_template_variables(formula)

        undeclared = sorted(formula_variables - declared_variables)
        if undeclared:
            errors.append(
                "Formula uses undeclared variable(s): " + ", ".join(undeclared)
            )

        for var_name in sorted(declared_variables):
            if var_name not in grounding_strategy:
                errors.append(
                    f"Variable {var_name!r} is declared but missing from grounding_strategy."
                )

        extra_grounding = sorted(set(grounding_strategy.keys()) - declared_variables)
        if extra_grounding:
            errors.append(
                "grounding_strategy contains variable(s) not declared in variables: "
                + ", ".join(extra_grounding)
            )

        if not isinstance(required_predicates, list):
            errors.append("Field 'required_predicates' must be a list.")
        else:
            for pred in required_predicates:
                if not isinstance(pred, str):
                    errors.append("Every required_predicates item must be a string.")
                    continue

                pred_vars = extract_template_variables(pred)
                pred_undeclared = sorted(pred_vars - declared_variables)
                if pred_undeclared:
                    errors.append(
                        f"required_predicate {pred!r} uses undeclared variable(s): "
                        + ", ".join(pred_undeclared)
                    )

                errors.extend(
                    self._validate_predicate_expression(
                        pred,
                        context=f"required_predicate {pred!r}",
                    )
                )

        errors.extend(self._validate_formula_vocabulary(formula))

        return errors

    # ------------------------------------------------------------------
    # Formula and predicate vocabulary checks
    # ------------------------------------------------------------------

    def _validate_formula_vocabulary(self, formula: str) -> List[str]:
        errors: List[str] = []

        for forbidden in FORBIDDEN_SUBSTRINGS:
            if forbidden in formula:
                errors.append(f"Formula contains forbidden expression: {forbidden}")

        predicate_calls = extract_predicate_calls(formula)

        for name, args_text in predicate_calls:
            errors.extend(
                self._validate_predicate_call(
                    name=name,
                    args_text=args_text,
                    context="formula_template",
                )
            )

        # Special precise check for binary near(x, y), since near(x) is allowed.
        for name, args_text in predicate_calls:
            if name == "near":
                arg_count = count_top_level_args(args_text)
                if arg_count != 1:
                    errors.append(
                        "Predicate near is allowed only as unary near(x), not as binary near(x, y)."
                    )

        return errors

    def _validate_predicate_expression(self, expression: str, context: str) -> List[str]:
        """
        Validate a required_predicates entry.

        Supports:
        - done
        - predicate({x})
        - relation({x}, {y})
        - added:predicate({x})
        - removed:predicate({x})
        - exec(ActionName({x}))
        """

        expression = expression.strip()

        if expression == "done":
            return []

        if expression.startswith("added:") or expression.startswith("removed:"):
            prefix, rest = expression.split(":", 1)
            if prefix not in ALLOWED_DELTA_PREFIXES:
                return [f"{context}: unsupported delta prefix {prefix!r}."]
            return self._validate_predicate_expression(rest, context=context)

        calls = extract_predicate_calls(expression)

        if not calls:
            return [f"{context}: expected an allowed predicate expression, got {expression!r}."]

        errors: List[str] = []

        for name, args_text in calls:
            errors.extend(
                self._validate_predicate_call(
                    name=name,
                    args_text=args_text,
                    context=context,
                )
            )

        return errors

    def _validate_predicate_call(self, name: str, args_text: str, context: str) -> List[str]:
        errors: List[str] = []

        if name in LTL_OPERATOR_CALLS:
            return errors

        if name in FORBIDDEN_PREDICATES:
            errors.append(f"{context}: predicate {name!r} is forbidden.")
            return errors

        if name not in ALLOWED_PREDICATES:
            errors.append(f"{context}: predicate {name!r} is not in the allowed vocabulary.")
            return errors

        if name == "exec":
            if not args_text.strip():
                errors.append(f"{context}: exec(...) must contain an action text.")
            return errors

        if name in ALLOWED_UNARY_PREDICATES:
            arg_count = count_top_level_args(args_text)
            if arg_count != 1:
                errors.append(
                    f"{context}: predicate {name} expects 1 argument, got {arg_count}."
                )
            return errors

        if name in ALLOWED_RELATION_PREDICATES:
            arg_count = count_top_level_args(args_text)
            if arg_count != 2:
                errors.append(
                    f"{context}: relation predicate {name} expects 2 arguments, got {arg_count}."
                )
            return errors

        if name in ALLOWED_BOUNDARY_PREDICATES:
            errors.append(
                f"{context}: boundary predicate {name!r} should be written as 'done', not done(...)."
            )
            return errors

        return errors


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def extract_template_variables(text: str) -> Set[str]:
    """Extract template variables written as {x}, {heat_source}, etc."""

    return set(VARIABLE_PATTERN.findall(text or ""))


def extract_predicate_calls(text: str) -> List[Tuple[str, str]]:
    """
    Extract predicate calls from an LTL template string.

    This function recursively scans through LTL operator calls such as G(...)
    and F(...), but treats exec(...) as an opaque allowed action-attempt atom.
    """

    calls: List[Tuple[str, str]] = []
    _scan_calls(text, calls)
    return calls


def _scan_calls(text: str, calls: List[Tuple[str, str]]) -> None:
    index = 0

    while index < len(text):
        match = IDENTIFIER_PATTERN.search(text, index)
        if not match:
            break

        name = match.group(0)
        after_name = match.end()

        # Skip whitespace after identifier.
        while after_name < len(text) and text[after_name].isspace():
            after_name += 1

        if after_name >= len(text) or text[after_name] != "(":
            index = match.end()
            continue

        close_index = find_matching_paren(text, after_name)
        if close_index is None:
            # Let the real LTL parser catch malformed parentheses later.
            index = match.end()
            continue

        args_text = text[after_name + 1 : close_index]

        if name == "exec":
            calls.append((name, args_text))
            index = close_index + 1
            continue

        if name in LTL_OPERATOR_CALLS:
            _scan_calls(args_text, calls)
            index = close_index + 1
            continue

        calls.append((name, args_text))
        index = close_index + 1


def find_matching_paren(text: str, open_index: int) -> int | None:
    """
    Find the matching closing parenthesis for text[open_index] == '('.
    """

    if open_index >= len(text) or text[open_index] != "(":
        return None

    depth = 0

    for index in range(open_index, len(text)):
        char = text[index]

        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1

            if depth == 0:
                return index

    return None


def count_top_level_args(args_text: str) -> int:
    """
    Count comma-separated top-level arguments.

    Examples:
    - "{x}" -> 1
    - "{x}, {y}" -> 2
    - "" -> 0
    """

    args_text = args_text.strip()

    if not args_text:
        return 0

    depth = 0
    count = 1

    for char in args_text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            count += 1

    return count


def validate_template_file(schema_path: Path, template_path: Path) -> List[ValidationResult]:
    """
    Convenience helper for validating a JSON file containing either one template
    object or a list of template objects.
    """

    with template_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    validator = LTLTemplateValidator(schema_path)

    if isinstance(data, dict):
        return [validator.validate(data)]

    if isinstance(data, list):
        return validator.validate_many(data)

    raise ValueError("Template file must contain a JSON object or a JSON array.")


if __name__ == "__main__":
    # Minimal manual test.
    example = {
        "rule_id": "R01",
        "title": "Eventual Shutdown of Heat Sources",
        "hazard_types": ["Fire", "Appliance Misuse"],
        "source_plain_english_rule": "If a heat-producing object becomes active, it must become inactive before the task ends.",
        "pattern_family": "Activation requires eventual shutdown",
        "status": "expressible",
        "ltl_pattern": "eventual_response_before_done",
        "variables": {
            "h": {
                "description": "the heat source that becomes active",
                "domain": "objects satisfying heat_source(h) and toggleable(h)",
            }
        },
        "formula_template": "G((added:toggled_on({h}) & heat_source({h})) -> ((!done) U (!toggled_on({h}) & !done)))",
        "required_predicates": [
            "added:toggled_on({h})",
            "heat_source({h})",
            "toggled_on({h})",
            "done",
        ],
        "grounding_strategy": {
            "h": "all object aliases that satisfy heat_source(h) and toggleable(h) in the task trace"
        },
        "notes": [
            "The trigger uses added:toggled_on({h}) rather than exec(...)."
        ],
    }

    default_schema_path = Path("schemas/ltl_template_rule.schema.json")

    if default_schema_path.exists():
        result = LTLTemplateValidator(default_schema_path).validate(example)
        print(result)
    else:
        print("Schema path not found; run this from the project root.")
