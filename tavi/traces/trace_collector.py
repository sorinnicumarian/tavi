import json
from datetime import datetime, timezone


OBJECT_FIELDS = [
    "objectId",
    "objectType",
    "position",
    "parentReceptacles",
    "isPickedUp",
    "visible",
    "isOpen",
    "isToggled",
    "isCooked",
    "isBroken",
    "isDirty",
    "isFilledWithLiquid",
    "isSliced",
]


def process_state(metadata):

    facts = []

    for obj in metadata.get("objects", []):

        obj_name = obj.get("objectType")

        if obj.get("visible"):
            facts.append(f"visible({obj_name})")

        if obj.get("isOpen"):
            facts.append(f"open({obj_name})")

        if obj.get("isPickedUp"):
            facts.append(f"holding({obj_name})")

        if obj.get("isCooked"):
            facts.append(f"cooked({obj_name})")

        if obj.get("isDirty"):
            facts.append(f"dirty({obj_name})")

        if obj.get("isBroken"):
            facts.append(f"broken({obj_name})")

        if obj.get("isFilledWithLiquid"):
            facts.append(f"filled({obj_name})")

    return sorted(list(set(facts)))


class TraceCollector:

    def __init__(
        self,
        output_path,
        episode_id,
        scene_name,
        instruction
    ):

        self.output_path = output_path

        self.episode_id = episode_id

        self.scene_name = scene_name

        self.instruction = instruction

        self.step_id = 0

    def capture_step(
        self,
        action_name,
        pre_metadata,
        post_metadata,
        success=True,
        error=None
    ):

        pre_facts = process_state(pre_metadata)

        post_facts = process_state(post_metadata)

        agent = post_metadata.get("agent", {})

        record = {

            "episode_id": self.episode_id,

            "scene_name": self.scene_name,

            "instruction": self.instruction,

            "step_id": self.step_id,

            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "action": action_name,

            "facts": post_facts,

            "facts_delta": {

                "added": sorted(
                    set(post_facts) - set(pre_facts)
                ),

                "removed": sorted(
                    set(pre_facts) - set(post_facts)
                ),
            },

            "state": {

                "agent": {

                    "position": agent.get("position"),

                    "rotation": agent.get("rotation"),
                },

                "inventory": post_metadata.get(
                    "inventoryObjects",
                    []
                ),

                "objects": [

                    {
                        f: o.get(f)
                        for f in OBJECT_FIELDS
                    }

                    for o in post_metadata.get(
                        "objects",
                        []
                    )
                ],
            },

            "outcome": {
                "success": success,
                "error": error
            },
        }

        with open(
            self.output_path,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(json.dumps(record) + "\n")

        print(
            f"step {self.step_id:03d} | "
            f"{action_name} | "
            f"{'OK' if success else error}"
        )

        self.step_id += 1