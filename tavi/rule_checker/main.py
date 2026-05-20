from flloat.parser.ltlf import LTLfParser

# parse the formula
parser = LTLfParser()
formula = "G(a -> F(b))"
parsed_formula = parser(formula)

# evaluate over finite traces
t1 = [
    {"a": False, "b": False},
    {"a": True, "b": False},
    {"a": True, "b": False},
    {"a": True, "b": True},
    {"a": False, "b": False},
]
assert parsed_formula.truth(t1, 0)
t2 = [
    {"a": False, "b": False},
    {"a": True, "b": False},
    {"a": False, "b": False},
]
assert not parsed_formula.truth(t2, 0)

# from LTLf formula to DFA
dfa = parsed_formula.to_automaton()
assert dfa.accepts(t1)
assert not dfa.accepts(t2)

print("All tests passed successfully.")