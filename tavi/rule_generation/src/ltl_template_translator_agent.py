"""
Agent wrapper for the LTL-template generation stage.

This class is intentionally small.

Responsibility:
- receive a fully rendered prompt
- call the LLM
- return the raw text response

It does NOT:
- build prompts
- parse JSON
- validate schemas
- check LTL correctness

Those jobs belong to:
- ltl_template_generation_config.py
- ltl_template_response_parser.py
- ltl_template_validator.py
"""

from __future__ import annotations

from typing import Any


class LTLTemplateTranslatorAgent:
    """
    Thin wrapper around the model used for LTL-template generation.

    The model_client can be:
    1. an object with generate_content(prompt)
    2. an object with generate(prompt)
    3. a callable that accepts prompt and returns text/response
    """

    def __init__(self, model_client: Any):
        self.model_client = model_client

    def translate(self, prompt: str) -> str:
        """
        Translate one rendered prompt into a raw LLM response.

        Parameters
        ----------
        prompt:
            Fully rendered prompt containing one plain-English rule.

        Returns
        -------
        str
            Raw text response from the model.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Prompt is empty.")

        response = self._call_model(prompt)
        return self._extract_text(response)

    def _call_model(self, prompt: str) -> Any:
        """Call the underlying model client."""

        if hasattr(self.model_client, "generate_content"):
            return self.model_client.generate_content(prompt)

        if hasattr(self.model_client, "generate"):
            return self.model_client.generate(prompt)

        if callable(self.model_client):
            return self.model_client(prompt)

        raise TypeError(
            "Unsupported model_client. Expected generate_content(prompt), "
            "generate(prompt), or a callable."
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        """
        Extract text from common model response shapes.

        Supports:
        - plain string
        - Gemini-style response.text
        - dictionary with 'text'
        - fallback to str(response)
        """

        if isinstance(response, str):
            return response

        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text

        if isinstance(response, dict) and isinstance(response.get("text"), str):
            return response["text"]

        return str(response)


if __name__ == "__main__":
    # Tiny local sanity check using a fake model.
    class FakeModel:
        def generate_content(self, prompt: str):
            return '{"rule_id": "R01", "status": "expressible"}'

    agent = LTLTemplateTranslatorAgent(FakeModel())
    print(agent.translate("Translate this rule."))
