import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from tavi.traces.state_processor import action_fact, build_id_map, process_state
from tavi.trace_translator.main import convert_json

logger = logging.getLogger(__name__)


class TraceCollector:
    """
    Records one JSONL line per agent step.

    Two usage modes:
      - Wrapping mode: pass a controller and call step() — wraps controller.step().
      - Manual mode: pass no controller and call capture_step() with pre/post metadata.
        Used by the SafeAgentBench loop where controller.step() is called externally.

    Live checking:
      Pass on_step=<callable> to hook into each step as it is recorded.
      The callable receives the translated facts dict (same format as the
      translated JSONL — predicate__arg keys, bool values).
      Return False from the callback to signal that execution should stop;
      capture_step() will then return False and the caller must break its loop.

      Example:
          def check(facts: dict) -> bool:
              if facts.get("holding__knife_1") and facts.get("near__child_1"):
                  return False  # violation — stop
              return True

          collector = TraceCollector(..., on_step=check)
    """

    def __init__(
        self,
        output_path: str,
        task_id: str | int = "",
        scene_name: str = "",
        instruction: str = "",
        controller=None,
        on_step: Callable[[dict], bool] | None = None,
    ):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.objects_output_path = self.output_path.with_name(
            self.output_path.stem + "_objects.jsonl"
        )
        self.translated_output_path = self.output_path.with_name(
            self.output_path.stem + "_translated.jsonl"
        )

        self.task_id = task_id
        self.scene_name = scene_name
        self.instruction = instruction
        self.controller = controller
        self.on_step = on_step
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
    ) -> bool:
        """Returns False if the on_step callback requested a stop, True otherwise."""
        self._ensure_id_map(pre_metadata)
        return self._record(action_name, action_args or {}, pre_metadata, post_metadata, success, error)

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
    ) -> bool:
        """Returns False if on_step callback requested a stop, True otherwise."""
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

        objects_record = {
            "task_id": self.task_id,
            "step_id": self.step_id,
            "object_ids": list(self._id_map.values())
        }
        
        with self.objects_output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(objects_record) + "\n")

        logger.debug("step %03d | %s | %s", self.step_id, action_name, "OK" if success else error)
        print(f"  step {self.step_id:03d}  {action_name:30s} → {'OK' if success else f'FAILED: {error}'}")
        self.step_id += 1

        translated = convert_json(record)
        with self.translated_output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(translated) + "\n")

        if self.on_step is not None:
            return self.on_step(translated)
        return True
