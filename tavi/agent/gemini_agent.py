import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

AVAILABLE_ACTIONS = [
    "MoveAhead", "MoveBack", "RotateRight", "RotateLeft",
    "LookUp", "LookDown", "PickupObject", "DropHandObject",
    "OpenObject", "CloseObject", "ToggleObjectOn", "ToggleObjectOff",
    "DONE",
]

# Actions that take no arguments — strip any args Gemini might hallucinate
NO_ARGS_ACTIONS = {
    "MoveAhead", "MoveBack", "RotateRight", "RotateLeft",
    "LookUp", "LookDown", "DropHandObject", "DONE",
}

SYSTEM_PROMPT = (
    "You are an embodied agent in a household simulation.\n\n"
    "Rules:\n"
    "- Only use objectIds that appear exactly in the 'visible objects' list. Never invent objectIds.\n"
    "- Do NOT repeat the same action if it just failed.\n"
    "- Do NOT repeat the same action more than twice in a row.\n"
    "- If you cannot move in one direction, rotate and try a different direction.\n"
    "- Signal DONE only when the task is fully complete.\n\n"
    'Respond with JSON only: {"action": "<action>", "args": {"objectId": "<exact_id>"} or null}\n\n'
    "Available actions: " + ", ".join(AVAILABLE_ACTIONS) + "\n"
    "objectId required for: PickupObject, OpenObject, CloseObject, ToggleObjectOn, ToggleObjectOff."
)


class GeminiAgent:
    def __init__(self, max_steps: int = 20):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.client = genai.Client(api_key=api_key)
        self.max_steps = max_steps
        self.history: list[str] = []

    def decide(
        self,
        visible_objects: list[dict],
        facts: list[str],
        task: str = "",
        all_object_types: list[str] | None = None,
        last_outcome: str | None = None,
        extra_instructions: str = "",
    ) -> tuple[str, dict]:
        visible_summary = [
            {"objectId": o["objectId"], "objectType": o["objectType"], "isPickedUp": o.get("isPickedUp")}
            for o in visible_objects
        ]

        repeated = len(self.history) >= 2 and self.history[-1] == self.history[-2]

        prompt = (
            f"Task: {task}\n"
            + (f"Hint: {extra_instructions}\n" if extra_instructions else "")
            + f"All object types present in scene: {all_object_types}\n"
            f"Visible objects right now (ONLY use objectIds from this list): {json.dumps(visible_summary)}\n"
            f"Current facts: {facts}\n"
            f"Action history (last 10): {self.history[-10:]}\n"
            + (f"Last action outcome: {last_outcome}\n" if last_outcome else "")
            + ("WARNING: Same action repeated twice in a row — choose something different.\n" if repeated else "")
            + "What is your next action?"
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )

        parsed = json.loads(response.text)
        action = parsed.get("action", "DONE")
        args = {} if action in NO_ARGS_ACTIONS else (parsed.get("args") or {})

        self.history.append(action)
        usage = response.usage_metadata
        print(f"    [tokens] prompt={usage.prompt_token_count} response={usage.candidates_token_count} thinking={usage.thoughts_token_count} total={usage.total_token_count}")
        return action, args
