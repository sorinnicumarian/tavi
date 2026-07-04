from __future__ import annotations


def collect_atoms(steps: list[dict[str, bool]]) -> set[str]:
    """
    Return all atoms that appear in a task trace.

    Input shape:
        [
            {"heat_source__candle_1": True, ...},
            {"added__toggled_on__candle_1": True, ...},
        ]
    """
    atoms: set[str] = set()

    for step in steps:
        atoms.update(step.keys())

    return atoms


def extract_unary_objects(atoms: set[str], predicate: str) -> set[str]:
    """
    Extract object ids from unary atoms.

    Example:
        predicate = "heat_source"
        atoms contains "heat_source__candle_1"

    Returns:
        {"candle_1"}
    """
    prefix = f"{predicate}__"
    return {
        atom[len(prefix):]
        for atom in atoms
        if atom.startswith(prefix) and "__" not in atom[len(prefix):]
    }


def extract_binary_pairs(atoms: set[str], relation: str) -> set[tuple[str, str]]:
    """
    Extract object pairs from binary relation atoms.

    Example:
        relation = "on"
        atoms contains "on__mug_1__table_1"

    Returns:
        {("mug_1", "table_1")}
    """
    prefix = f"{relation}__"
    pairs: set[tuple[str, str]] = set()

    for atom in atoms:
        if not atom.startswith(prefix):
            continue

        rest = atom[len(prefix):]
        parts = rest.split("__")

        if len(parts) == 2:
            pairs.add((parts[0], parts[1]))

    return pairs


def extract_added_objects(atoms: set[str], predicate: str) -> set[str]:
    """
    Extract object ids from added unary atoms.

    Example:
        predicate = "toggled_on"
        atoms contains "added__toggled_on__candle_1"

    Returns:
        {"candle_1"}
    """
    return extract_unary_objects(atoms, f"added__{predicate}")


def extract_removed_objects(atoms: set[str], predicate: str) -> set[str]:
    """
    Extract object ids from removed unary atoms.

    Example:
        predicate = "holding"
        atoms contains "removed__holding__mug_1"

    Returns:
        {"mug_1"}
    """
    return extract_unary_objects(atoms, f"removed__{predicate}")


def extract_added_pairs(atoms: set[str], relation: str) -> set[tuple[str, str]]:
    """
    Extract object pairs from added binary relation atoms.

    Example:
        relation = "on"
        atoms contains "added__on__mug_1__table_1"

    Returns:
        {("mug_1", "table_1")}
    """
    return extract_binary_pairs(atoms, f"added__{relation}")


def extract_removed_pairs(atoms: set[str], relation: str) -> set[tuple[str, str]]:
    """
    Extract object pairs from removed binary relation atoms.

    Example:
        relation = "on"
        atoms contains "removed__on__mug_1__table_1"

    Returns:
        {("mug_1", "table_1")}
    """
    return extract_binary_pairs(atoms, f"removed__{relation}")


def atom_exists(atoms: set[str], atom: str) -> bool:
    """Small readability helper."""
    return atom in atoms
