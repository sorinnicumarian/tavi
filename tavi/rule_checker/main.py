from flloat.parser.ltlf import LTLfParser
import os
import json
import re
from itertools import product

_TAVI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_TAVI_ROOT, ".."))

RULES_INPUT_FILE = os.path.join(
    _TAVI_ROOT,
    "rule_generation",
    "outputs",
    "rules_static.json"
)

TRACES_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "traces", "jsonl",
    "safeagentbench_abstract_traces_translated.jsonl"
)

OBJECTS_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "traces", "jsonl",
    "safeagentbench_abstract_traces_objects.jsonl"
)

def rule_json_to_list():
    """Returns list of (rule_id, title, formula_template) for expressible rules."""
    rules = []

    with open(RULES_INPUT_FILE, "r") as f:
        rules_data = json.load(f)

    for rule in rules_data:
        if rule["status"] != "not_expressible_with_current_trace_predicates":
            rules.append((rule["rule_id"], rule["title"], rule["formula_template"]))

    return rules

def get_task_object_ids(task_id):
    """
    Returns sorted list of object SIDs for a task.
    Reads from the objects sidecar file if available, otherwise extracts
    SIDs from predicate keys in the translated trace.
    """
    if os.path.exists(OBJECTS_INPUT_FILE):
        object_ids = set()
        with open(OBJECTS_INPUT_FILE, "r") as f:
            for line in f:
                record = json.loads(line)
                if record["task_id"] == task_id:
                    object_ids.update(record["object_ids"])
        return sorted(object_ids)

    # Fallback: extract object SIDs from fact keys in the translated trace.
    # SIDs look like "knife_1", "candle_1" — a word followed by underscore and digits.
    # We extract the last token from keys like "heat_source__candle_1", "on__cloth_1__shelf_1".
    object_ids = set()
    _sid_re = re.compile(r"[a-z][a-z]*_\d+$")
    with open(TRACES_INPUT_FILE, "r") as f:
        for line in f:
            record = json.loads(line)
            if record.get("record_type") in ("task_start", "task_end", "task_separator"):
                continue
            if record.get("task_id") != task_id:
                continue
            for key in record.get("facts", {}):
                if key == "done":
                    continue
                parts = key.split("__")
                for part in parts[1:]:  # skip the predicate name (first segment)
                    if _sid_re.fullmatch(part):
                        object_ids.add(part)
    return sorted(object_ids)

def prepare_traces_for_checking(traces):
    """
    Convert a list of translated step dicts into a list of flat bool dicts
    for flloat. Each step dict gets its exec__ key (if any) merged into facts.
    """
    result = []

    for record in traces:
        step_facts = dict(record["facts"])

        # merge exec key into facts so flloat can see it
        # flloat's LTLf parser only accepts lowercase symbol names, so we lowercase
        for key, value in record.items():
            if key.startswith("exec__"):
                step_facts[key.lower()] = value

        result.append(step_facts)

    return result

def instantiate_rules(rule_templates, task_id, object_ids: list[str] | None = None):
    """
    Instantiate parametric rule templates by substituting concrete object IDs.
    Returns list of (rule_id, title, grounded_formula).

    rule_templates may be a list of (rule_id, title, formula) tuples
    or a list of rule dicts (from auto_generate / rules_ltl_templates.json).

    object_ids: if provided, use these directly instead of reading from file.
    """
    instantiated = []
    if object_ids is None:
        object_ids = get_task_object_ids(task_id)

    def _as_tuple(r):
        if isinstance(r, dict):
            return r["rule_id"], r["title"], r["formula_template"]
        return r

    for entry in rule_templates:
        if isinstance(entry, dict):
            if entry.get("status") == "not_expressible_with_current_trace_predicates":
                continue
            if not entry.get("formula_template"):
                continue
        rule_id, title, template = _as_tuple(entry)
        # Normalize any PascalCase literals in the formula to snake_case for flloat
        template = re.sub(
            r'(?<=[_a-z])([A-Z][a-zA-Z0-9]*)',
            lambda m: re.sub(r'(?<!^)(?=[A-Z])', '_', m.group(1)).lower(),
            template
        )
        vars_ = sorted(set(re.findall(r"\{(\w+)\}", template)))

        if not vars_:
            instantiated.append((rule_id, title, template))
            continue

        # object_ids must be lowercase for flloat — normalize PascalCase to snake_case
        normalized_ids = [
            re.sub(r'(?<!^)(?=[A-Z])', '_', oid).lower() if re.search(r'[A-Z]', oid) else oid
            for oid in object_ids
        ]
        for values in product(normalized_ids, repeat=len(vars_)):
            mapping = dict(zip(vars_, values))
            instantiated.append((rule_id, title, template.format(**mapping)))

    return instantiated

def find_first_violating_step(traces_dict, parsed_formula):
    """
    Binary-search for the earliest step prefix at which the formula is violated.
    Returns the 0-based step index, or None if the full trace satisfies the formula.
    """
    for i in range(1, len(traces_dict) + 1):
        if not parsed_formula.truth(traces_dict[:i]):
            return i - 1
    return None

def check_rules(traces, task_id, rules: list | None = None, object_ids: list[str] | None = None):
    """
    Check LTL rules against a task trace.

    rules: optional pre-generated list of rule dicts (from auto_generate or rule_json_to_list).
           If None, falls back to the static rules_ltl_templates.json file.
    object_ids: if provided, used for template instantiation instead of reading from file.
    """
    traces_dict = prepare_traces_for_checking(traces)
    raw_rules = rules if rules is not None else rule_json_to_list()
    rules_list = instantiate_rules(raw_rules, task_id, object_ids=object_ids)

    parser = LTLfParser()

    violations = []
    for rule_id, title, formula in rules_list:
        try:
            parsed = parser(formula)
        except Exception as e:
            logging.warning(f"Skipping unparseable formula [{rule_id}]: {e} — {formula[:80]}")
            continue
        if not parsed.truth(traces_dict):
            step = find_first_violating_step(traces_dict, parsed)
            action = traces[step]["action"]["name"] if step is not None and step < len(traces) else "unknown"
            violations.append({
                "rule_id": rule_id,
                "title": title,
                "formula": formula,
                "first_violating_step": step,
                "action_at_step": action,
            })

    violated = len(violations) > 0
    if violated:
        v = violations[0]
        message = (
            f"[{v['rule_id']}] {v['title']} — "
            f"step {v['first_violating_step']} ({v['action_at_step']}) — "
            f"{v['formula']}"
        )
    else:
        message = "All rules are satisfied."

    return (violated, message, violations, traces_dict)