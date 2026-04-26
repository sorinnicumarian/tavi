import json
from datetime import datetime, timezone
from pathlib import Path

from ai2thor.controller import Controller
from tavi.traces.state_processor import process_state

OBJECT_FIELDS = [
    "objectId", "objectType", "position", "parentReceptacles",
    "isPickedUp", "visible", "isOpen", "isToggled",
    "isCooked", "isBroken", "isDirty", "isFilledWithLiquid", "isSliced",
]


class TraceCollector:
    def __init__(self, controller: Controller, output_path: str):
        self.controller = controller
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.step_id = 0

    def step(self, action: str, **kwargs) -> bool:
        pre_facts = process_state(self.controller.last_event.metadata)

        event = self.controller.step(action=action, **kwargs)
        metadata = self.controller.last_event.metadata
        post_facts = process_state(metadata)

        success = event.metadata["lastActionSuccess"]
        error = event.metadata.get("errorMessage") or None
        agent = metadata.get("agent", {})

        self._write({
            "step_id": self.step_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {"name": action, "args": kwargs or None},
            "facts": post_facts,
            "facts_delta": {
                "added": sorted(set(post_facts) - set(pre_facts)),
                "removed": sorted(set(pre_facts) - set(post_facts)),
            },
            "state": {
                "agent": {"position": agent.get("position"), "rotation": agent.get("rotation")},
                "objects": [{f: o.get(f) for f in OBJECT_FIELDS} for o in metadata.get("objects", [])],
            },
            "outcome": {"success": success, "error": error},
        })

        print(f"  step {self.step_id:02d}  {action:30s} → {'OK' if success else f'FAILED: {error}'}")
        self.step_id += 1
        return success

    def _write(self, record: dict):
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
