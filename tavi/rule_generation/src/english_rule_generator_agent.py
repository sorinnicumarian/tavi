import json
import logging
import os
from pydoc import text

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class EnglishRuleGeneratorAgent:
    client: str
    max_steps: float
    
    def __init__(self, max_steps: int = 20):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.client = genai.Client(api_key=api_key)
        self.max_steps = max_steps
        self.history: list[str] = []
        
        
    def generate_rules(self, prompt: str) -> list[str]:
        
        response = self.client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=1024),
                
            ),
        )

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

        return text.strip()
        
