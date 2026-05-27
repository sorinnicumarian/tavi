from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleTemplate:
    """
    Parametric LTL rule template.

    For now this supports the simple first prototype:
    - one main variable, like {h}
    - one trigger atom pattern
    - optional guard atom patterns
    - one LTL formula template string
    """

    rule_id: str
    description: str

    # Variable name used inside the template, e.g. "h" for {h}
    variable: str

    # Atom pattern that tells the grounder which objects are relevant.
    # Example: "added__toggled_on__{h}"
    trigger: str

    # Guard atoms that must also appear for the same binding.
    # Example: ["heat_source__{h}"]
    guards: list[str]

    # flloat-ready LTL formula template.
    # Example: "G((added__toggled_on__{h} & heat_source__{h}) -> F(removed__toggled_on__{h}))"
    formula_template: str


def fill_template(template: str, variable: str, value: str) -> str:
    """
    Replace a template variable with a concrete object id.

    Example:
        fill_template("heat_source__{h}", "h", "candle_1")
        -> "heat_source__candle_1"
    """
    return template.replace("{" + variable + "}", value)


def default_rule_templates() -> list[RuleTemplate]:
    """
    First small set of manually written rule templates.

    Keep this intentionally small at the beginning.
    We add more rules only after the checker works end-to-end.
    """
    return [
        RuleTemplate(
            rule_id="R_HEAT_SOURCE_SHUTDOWN",
            description=(
                "If a heat source is turned on, it must be turned off before task_end."
            ),
            variable="h",
            trigger="added__toggled_on__{h}",
            guards=["heat_source__{h}"],
            formula_template=(
                "G((added__toggled_on__{h} & heat_source__{h}) "
                "-> F(removed__toggled_on__{h}))"
            ),
        ),
    ]
