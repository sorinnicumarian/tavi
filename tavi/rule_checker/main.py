from flloat.parser.ltlf import LTLfParser
import os
import json
import re
from itertools import product

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

RULES_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "rule_generation",
    "outputs",
    "rules_ltl_templates.json"
)

TRACES_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "..",
    "traces",
    "safeagentbench_abstract_traces_translated.jsonl"
)

OBJECTS_INPUT_FILE = os.path.join(
    _REPO_ROOT,
    "..",
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
    object_ids = set()

    with open(OBJECTS_INPUT_FILE, "r") as f:
        for line in f:
            record = json.loads(line)

            if record["task_id"] == task_id:
                object_ids.update(record["object_ids"])

    return sorted(object_ids)

def prepare_traces_for_checking(traces):
    result = []
    action_key = ""
    action_value = ""

    for line in traces:
            result.append(line["facts"])
            
            for key in line:
                if key.startswith("exec"):
                    action_key = key
                    action_value = line[action_key]

    if result:
        result.pop()

    result.append({action_key: action_value})     

    return result

def instantiate_rules(rule_templates, task_id):
    instantiated = []
    object_ids = get_task_object_ids(task_id)

    for template in rule_templates:
        vars_ = sorted(set(re.findall(r"\{(\w+)\}", template)))

        if not vars_:
            instantiated.append(template)
            continue

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