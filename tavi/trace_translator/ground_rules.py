from __future__ import annotations

import re
from dataclasses import dataclass

from atom_utils import collect_atoms
from rule_templates import RuleTemplate, fill_template


@dataclass(frozen=True)
class GroundedRule:
    """Concrete LTL formula produced from a rule template and one binding."""

    rule_id: str
    description: str
    binding: dict[str, str]
    formula: str


def _trigger_regex(trigger_template: str, variable: str) -> re.Pattern[str]:
    """
    Convert a trigger template into a regex.

    Example:
        "added__toggled_on__{h}"
        -> matches "added__toggled_on__candle_1"
    """
    placeholder = "{" + variable + "}"
    escaped = re.escape(trigger_template)
    escaped_placeholder = re.escape(placeholder)

    pattern = escaped.replace(
        escaped_placeholder,
        rf"(?P<{variable}>[A-Za-z0-9_]+)",
    )

    return re.compile(rf"^{pattern}$")


def ground_rule_template(
    steps: list[dict[str, bool]],
    template: RuleTemplate,
) -> list[GroundedRule]:
    """
    Ground one rule template against one task trace.

    Non-exhaustive strategy:
    - Look only at atoms that actually appear in the trace.
    - A binding is created only when the template trigger appears.
    - Guards must also appear somewhere in the same trace.
    """
    atoms = collect_atoms(steps)
    regex = _trigger_regex(template.trigger, template.variable)

    grounded: list[GroundedRule] = []
    seen_bindings: set[str] = set()

    for atom in sorted(atoms):
        match = regex.match(atom)
        if match is None:
            continue

        value = match.group(template.variable)

        if value in seen_bindings:
            continue

        guards_hold = all(
            fill_template(guard, template.variable, value) in atoms
            for guard in template.guards
        )

        if not guards_hold:
            continue

        formula = fill_template(
            template.formula_template,
            template.variable,
            value,
        )

        grounded.append(
            GroundedRule(
                rule_id=template.rule_id,
                description=template.description,
                binding={template.variable: value},
                formula=formula,
            )
        )

        seen_bindings.add(value)

    return grounded


def ground_all_rules(
    steps: list[dict[str, bool]],
    templates: list[RuleTemplate],
) -> list[GroundedRule]:
    """Ground all templates against one task trace."""
    grounded: list[GroundedRule] = []

    for template in templates:
        grounded.extend(ground_rule_template(steps, template))

    return grounded
