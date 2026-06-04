import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from tavi.traces.state_processor import action_fact, build_id_map, process_state

logger = logging.getLogger(__name__)


class TraceCollector:
    """
    Records one JSONL line per agent step.

    Two usage modes:
      - Wrapping mode: pass a controller and call step() — wraps controller.step().
      - Manual mode: pass no controller and call capture_step() with pre/post metadata.
        Used by Eldi's SafeAgentBench loop where controller.step() is called externally.
    """

    def __init__(
        self,
        output_path: str,
        task_id: str | int = "",
        scene_name: str = "",
        instruction: str = "",
        controller=None,
    ):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.scene_name = scene_name
        self.instruction = instruction
        self.controller = controller
        self.step_id = 0
        self._id_map: dict[str, str] = {}

    # ------------------------------------------------------------------
    # ID map — built lazily on first step so the scene is fully loaded
    # ------------------------------------------------------------------

    def _ensure_id_map(self, metadata: dict) -> None:
        if not self._id_map:
            self._id_map = build_id_map(metadata.get("objects", []))

    # ------------------------------------------------------------------
    # Wrapping mode (your original scenario loop)
    # ------------------------------------------------------------------

    def step(self, action: str, **kwargs) -> bool:
        if self.controller is None:
            raise RuntimeError("step() requires a controller — use capture_step() instead.")

        pre_metadata = self.controller.last_event.metadata
        self._ensure_id_map(pre_metadata)

        event = self.controller.step(action=action, **kwargs)
        post_metadata = event.metadata

        success = post_metadata["lastActionSuccess"]
        error = post_metadata.get("errorMessage") or None

        self._record(action, kwargs, pre_metadata, post_metadata, success, error)
        return success

    # ------------------------------------------------------------------
    # Manual mode (Eldi's SafeAgentBench loop)
    # ------------------------------------------------------------------

    def capture_step(
        self,
        action_name: str,
        pre_metadata: dict,
        post_metadata: dict,
        action_args: dict | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self._ensure_id_map(pre_metadata)
        self._record(action_name, action_args or {}, pre_metadata, post_metadata, success, error)

    # ------------------------------------------------------------------
    # Core record writer
    # ------------------------------------------------------------------

    def _record(
        self,
        action_name: str,
        action_args: dict,
        pre_metadata: dict,
        post_metadata: dict,
        success: bool,
        error: str | None,
    ) -> None:
        pre_facts = process_state(pre_metadata, self._id_map)
        post_facts = process_state(post_metadata, self._id_map)

        act = action_fact(action_name, action_args, self._id_map)

        pre_set = set(pre_facts)
        post_set = set(post_facts)

        agent = post_metadata.get("agent", {})

        # act is None for dropped actions (e.g. find) — exclude from facts
        post_set_with_exec = post_set | {act} if act is not None else post_set

        record = {
            "task_id": self.task_id,
            "scene_name": self.scene_name,
            "instruction": self.instruction,
            "step_id": self.step_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": {"name": action_name, "args": action_args or None},
            "exec": act,
            "facts": sorted(post_set_with_exec),
            "facts_delta": {
                "added": sorted(post_set - pre_set),
                "removed": sorted(pre_set - post_set),
            },
            "agent": {
                "position": agent.get("position"),
                "rotation": agent.get("rotation"),
            },
            "outcome": {"success": success, "error": error},
        }

        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        logger.debug("step %03d | %s | %s", self.step_id, action_name, "OK" if success else error)
        print(f"  step {self.step_id:03d}  {action_name:30s} → {'OK' if success else f'FAILED: {error}'}")
        self.step_id += 1
