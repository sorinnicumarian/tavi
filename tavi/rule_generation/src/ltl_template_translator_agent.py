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

import json
import os
from typing import Any

from google import genai
from google.genai import types


class LTLTemplateTranslatorAgent:
    """
    Thin wrapper around the model used for LTL-template generation.

    The model_client can be:
    1. an object with generate_content(prompt)
    2. an object with generate(prompt)
    3. a callable that accepts prompt and returns text/response
    """

    def __init__(
        self,
        model: str = "gemini-2.5-pro",
        temperature: float = 0.2,
        max_output_tokens: int = 8192,
        thinking_budget: int = 1024,
        max_revision_rounds = 2,
    ):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.thinking_budget = thinking_budget
        self.max_revision_rounds = max_revision_rounds
        self.history: list[str] = []

    def translate_rule(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is empty.")

        text = self._call_model(prompt)
        return text

    def _call_model(self, prompt: str) -> Any:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
                
            ),
        )
        
        print(f"Raw Gemini response:")
        print("prompt tokens:", response.usage_metadata.prompt_token_count)
        print("output tokens:", response.usage_metadata.candidates_token_count)
        print("total tokens:", response.usage_metadata.total_token_count)

        print("thinking tokens:", getattr(response.usage_metadata, "thoughts_token_count", None))
        print("cached tokens:", getattr(response.usage_metadata, "cached_content_token_count", None))
            
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise RuntimeError(
                "Gemini returned an empty response. "
                "Try a larger max_output_tokens, a different model, or inspect the raw API response."
            )

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Gemini returned invalid JSON:\n{text}"
            ) from exc
