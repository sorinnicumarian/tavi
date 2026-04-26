def process_state(metadata: dict) -> list[str]:
    """
    Reads AI2-THOR scene metadata and returns simple true/false facts per object.
    Examples: holding(knife), near(stove), on(knife,countertop), open(fridge)
    """
    facts = []
    objects = metadata.get("objects", [])
    held_ids = {o["objectId"] for o in objects if o.get("isPickedUp")}

    BOOLEAN_FACTS = [
        ("isPickedUp",        "holding"),
        ("visible",           "near"),
        ("isOpen",            "open"),
        ("isToggled",         "toggled_on"),
        ("isCooked",          "cooked"),
        ("isBroken",          "broken"),
        ("isDirty",           "dirty"),
        ("isFilledWithLiquid","filled_with_liquid"),
        ("isSliced",          "sliced"),
    ]

    for obj in objects:
        name = obj["objectType"].lower()

        for ai2thor_key, fact_name in BOOLEAN_FACTS:
            if obj.get(ai2thor_key):
                facts.append(f"{fact_name}({name})")

        for receptacle_id in (obj.get("parentReceptacles") or []):
            if receptacle_id not in held_ids:
                facts.append(f"on({name},{receptacle_id.split('|')[0].lower()})")

    return sorted(set(facts))
