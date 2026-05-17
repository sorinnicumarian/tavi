from __future__ import annotations

# ── Semantic categories (AI2-THOR has no built-in field for these) ────────────

# Objects that produce heat / act as ignition sources
HEAT_SOURCES = {
    "stoveburner", "stoveknob", "microwave", "toaster", "coffeemachine",
    "candle", "lightswitch", "lamp",
}
# Objects that can catch fire / burn
FLAMMABLE = {
    "papertowelroll", "book", "cloth", "dishsponge", "newspaper",
    "tissuebox", "towel", "handtowel", "toilet paper",
}
# Objects that break easily
FRAGILE = {
    "vase", "egg", "winebottle", "plate", "cup", "bowl", "glass",
    "bottle", "jar", "mirror", "window",
}
# Objects with sharp edges — dangerous if mishandled
SHARP = {"knife", "butterknife", "fork", "scissors", "shard"}
# Objects posing electrocution / short-circuit risk when wet
ELECTRICAL = {
    "laptop", "television", "microwave", "toaster", "cellphone",
    "alarmclock", "desklamp", "floorlamp",
}
# Objects that contain or transport chemicals / cleaning agents
CHEMICAL = {
    "spraybottle", "soapbottle", "dishsponge", "handtowelholder",
    "bottleofbleach",
}

_SEMANTIC_CATEGORIES: dict[str, set[str]] = {
    "heat_source": HEAT_SOURCES,
    "flammable":   FLAMMABLE,
    "fragile":     FRAGILE,
    "sharp":       SHARP,
    "electrical":  ELECTRICAL,
    "chemical":    CHEMICAL,
}

# ── Dynamic boolean states emitted directly from AI2-THOR metadata ────────────

_BOOLEAN_STATES: list[tuple[str, str]] = [
    ("isPickedUp",  "holding"),
    ("isOpen",      "open"),
    ("isToggled",   "toggled_on"),
    ("isCooked",    "cooked"),
    ("isBroken",    "broken"),
    ("isDirty",     "dirty"),
    ("isSliced",    "sliced"),
    ("isUsedUp",    "used_up"),
    ("isMoving",    "moving"),
]

# ── Static capability flags — emitted once, never change during a run ─────────
# Useful for LTL rules like "G(pickup_attempted → pickupable)"

_CAPABILITY_FLAGS: list[tuple[str, str]] = [
    ("pickupable",  "pickupable"),
    ("receptacle",  "receptacle"),
    ("openable",    "openable"),
    ("toggleable",  "toggleable"),
    ("breakable",   "breakable"),
    ("sliceable",   "sliceable"),
    ("cookable",    "cookable"),
    ("moveable",    "moveable"),
    ("dirtyable",   "dirtyable"),
    ("canFillWithLiquid", "can_fill_with_liquid"),
]

# Distance threshold (metres) below which an object is considered "near" agent
_NEAR_THRESHOLD = 1.5


def build_id_map(objects: list[dict]) -> dict[str, str]:
    """
    Assigns stable short IDs to AI2-THOR objectIds.
    e.g. Knife|-1.00|+0.90|+1.00  →  knife_1
    Sorted within each type for determinism across runs.
    """
    by_type: dict[str, list[str]] = {}
    for obj in objects:
        otype = obj["objectType"].lower()
        by_type.setdefault(otype, []).append(obj["objectId"])

    id_map: dict[str, str] = {}
    for otype, oids in by_type.items():
        for i, oid in enumerate(sorted(oids), start=1):
            id_map[oid] = f"{otype}_{i}"
    return id_map


def process_state(metadata: dict, id_map: dict[str, str]) -> list[str]:
    """
    Returns a flat list of ground predicates for the current world state.
    All object references use stable short IDs (e.g. knife_1, stove_1).

    Predicate vocabulary
    ────────────────────
    Spatial:
      has_position(id, x, y, z)       — world position (2 d.p.)
      on(id, receptacle_id)           — contained in / resting on receptacle
      near(id)                        — within _NEAR_THRESHOLD metres of agent
      visible(id)                     — currently in agent's camera frustum

    Dynamic states:
      holding(id)                     — agent is carrying this object
      open(id)                        — openable object is open
      toggled_on(id)                  — toggleable object is on
      cooked(id)                      — object has been cooked
      broken(id)                      — object is broken
      dirty(id)                       — object is dirty
      sliced(id)                      — object has been sliced
      used_up(id)                     — consumable has been used up
      moving(id)                      — object is currently moving
      hot(id)                         — temperature == "Hot"
      cold(id)                        — temperature == "Cold"
      filled_with(id, liquid)         — filled with water / wine / coffee
      heat_source_active(id)          — AI2-THOR native isHeatSource flag
      cold_source_active(id)          — AI2-THOR native isColdSource flag
      material(id, mat)               — salient material (Wood/Metal/Glass/…)

    Static capabilities (intrinsic properties, never change):
      pickupable(id), receptacle(id), openable(id), toggleable(id),
      breakable(id), sliceable(id), cookable(id), moveable(id),
      dirtyable(id), can_fill_with_liquid(id)

    Semantic safety categories (hardcoded vocabulary):
      heat_source(id), flammable(id), fragile(id), sharp(id),
      electrical(id), chemical(id)
    """
    facts: list[str] = []
    objects = metadata.get("objects", [])
    held_oids = {o["objectId"] for o in objects if o.get("isPickedUp")}

    for obj in objects:
        oid = obj["objectId"]
        sid = id_map.get(oid, oid.split("|")[0].lower() + "_?")
        otype = obj["objectType"].lower()

        # ── semantic safety categories ────────────────────────────────────────
        for category, members in _SEMANTIC_CATEGORIES.items():
            if otype in members:
                facts.append(f"{category}({sid})")

        # ── AI2-THOR native heat/cold source flags ────────────────────────────
        if obj.get("isHeatSource"):
            facts.append(f"heat_source_active({sid})")
        if obj.get("isColdSource"):
            facts.append(f"cold_source_active({sid})")

        # ── temperature state ─────────────────────────────────────────────────
        temp = obj.get("temperature")
        if temp == "Hot":
            facts.append(f"hot({sid})")
        elif temp == "Cold":
            facts.append(f"cold({sid})")

        # ── dynamic boolean states ────────────────────────────────────────────
        for ai2thor_key, predicate in _BOOLEAN_STATES:
            if obj.get(ai2thor_key):
                facts.append(f"{predicate}({sid})")

        # ── liquid fill ───────────────────────────────────────────────────────
        if obj.get("isFilledWithLiquid"):
            liquid = obj.get("fillLiquid") or "unknown"
            facts.append(f"filled_with({sid},{liquid})")

        # ── static capability flags ───────────────────────────────────────────
        for ai2thor_key, predicate in _CAPABILITY_FLAGS:
            if obj.get(ai2thor_key):
                facts.append(f"{predicate}({sid})")

        # ── salient materials ─────────────────────────────────────────────────
        for mat in obj.get("salientMaterials") or []:
            facts.append(f"material({sid},{mat.lower()})")

        # ── visibility and proximity ──────────────────────────────────────────
        if obj.get("visible"):
            facts.append(f"visible({sid})")
        dist = obj.get("distance")
        if dist is not None and dist <= _NEAR_THRESHOLD:
            facts.append(f"near({sid})")

        # ── world position ────────────────────────────────────────────────────
        pos = obj.get("position")
        if pos:
            facts.append(
                f"has_position({sid},{pos['x']:.2f},{pos['y']:.2f},{pos['z']:.2f})"
            )

        # ── containment (on) — not emitted for held objects ───────────────────
        if oid not in held_oids:
            for receptacle_oid in obj.get("parentReceptacles") or []:
                rsid = id_map.get(receptacle_oid, receptacle_oid.split("|")[0].lower() + "_?")
                facts.append(f"on({sid},{rsid})")

    return sorted(set(facts))


def action_fact(action_name: str, args: dict, id_map: dict[str, str]) -> str:
    """
    Returns exec(ActionName,object_sid) for the action taken this step.
    If no objectId in args, returns exec(ActionName).
    """
    object_id = args.get("objectId")
    if object_id:
        sid = id_map.get(object_id, object_id.split("|")[0].lower() + "_?")
        return f"exec({action_name},{sid})"
    return f"exec({action_name})"
