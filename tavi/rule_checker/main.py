from flloat.parser.ltlf import LTLfParser
import os
import json

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
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

def rule_json_to_list():
    rules = []
    
    with open(RULES_INPUT_FILE, "r") as f:
        rules_data = json.load(f)

    for rule in rules_data:
        rules.append(rule["formula_template"])

    return rules


def traces_jsonl_to_dict(jsonl_file):
    result = []
    action_key = ""
    action_value
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            result.append(obj["facts"])
            
            for key in obj:
                if key.startswith("exec"):
                    action_key = key
                    action_value = obj[action_key]

        if result:
            result.pop()

        result.append({action_key: action_value})

    return result



def check_rules():
    # parse the formula
    parser = LTLfParser()
    formula = "G(a -> F(b))"
    parsed_formula = parser(formula)

    # evaluate over finite traces
    assert not parsed_formula.truth(t2, 0)

    # from LTLf formula to DFA
    dfa = parsed_formula.to_automaton()
    assert dfa.accepts(t1)
    assert not dfa.accepts(t2)

    print("All tests passed successfully.")


result = traces_jsonl_to_dict(TRACES_INPUT_FILE)
print(result)