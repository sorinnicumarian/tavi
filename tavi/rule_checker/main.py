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
    "rules_ltl_templates.json"
)

TRACES_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "traces",
    "safeagentbench_abstract_traces_translated.jsonl"
)

OBJECTS_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "traces",
    "safeagentbench_abstract_traces_objects.jsonl"
)

def rule_json_to_list():
    rules = []
    
    with open(RULES_INPUT_FILE, "r") as f:
        rules_data = json.load(f)

    for rule in rules_data:
        if rule["status"] != "not_expressible_with_current_trace_predicates":
            rules.append(rule["formula_template"])

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
        for key, value in record.items():
            if key.startswith("exec__"):
                step_facts[key] = value

        result.append(step_facts)

    return result

def instantiate_rules(rule_templates, task_id):
    """
    Instantiate parametric rule templates by substituting concrete object IDs.
    Only substitutes object IDs that actually appear in the trace for this task,
    avoiding the combinatorial explosion of substituting all objects for all vars.
    """
    instantiated = []
    object_ids = get_task_object_ids(task_id)

    for template in rule_templates:
        vars_ = sorted(set(re.findall(r"\{(\w+)\}", template)))

        if not vars_:
            instantiated.append(template)
            continue

        # Each variable independently ranges over all object IDs
        # (vars may have different domains but we ground conservatively)
        for values in product(object_ids, repeat=len(vars_)):
            mapping = dict(zip(vars_, values))
            instantiated.append(template.format(**mapping))

    return instantiated

def check_rules(traces, task_id):

    traces_dict = prepare_traces_for_checking(traces)
    rules_list = instantiate_rules(rule_json_to_list(), task_id)
    
    # parse the formula
    parser = LTLfParser()

    rule_violated = False
    message = "All rules are satisfied."

    for rule in rules_list:
            parsed_formula = parser(rule)
            rule_violated = not parsed_formula.truth(traces_dict)

            if rule_violated:
                message = f"Rule violated: {rule}"
                break

    return (rule_violated, message, rules_list, traces_dict)