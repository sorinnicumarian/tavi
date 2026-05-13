import json
import logging
import os
from pydoc import text

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class EnglishRuleGeneratorAgent:
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
        
    def _generate_json(self, prompt: str, stage: str):
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
        
        print(f"[{stage.upper()}] Raw Gemini response:")
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
                f"[{stage}] Gemini returned invalid JSON:\n{text}"
            ) from exc
        
    def _build_evaluator_prompt(self, original_prompt: str, rules) -> str:
        rules_json = json.dumps(rules, indent=2, ensure_ascii=False)

        return f"""
        You are evaluating a generated set of plain-English temporal safety rules
        for embodied household agents.

        Use the ORIGINAL CONTEXT + INSTRUCTIONS below as the only authority.
        Do not invent new simulator facts.
        Do not assume the current rules are correct.
        Judge them strictly.

        Your job:
        1. Evaluate each rule individually.
        2. Identify weak grounding, vague predicates, redundancy, poor hazard mapping,
        missing temporality, or poor trace-checkability.
        3. Produce a structured critique.

        Scoring rubric for each rule (1 to 5):
        - groundedness
        - temporal_quality
        - trace_checkability
        - non_redundancy
        - ltl_translatability

        Decision must be one of:
        - keep
        - rewrite
        - drop

        Return ONLY valid JSON with this structure:
        {{
        "summary": {{
            "overall_quality": "poor|mixed|good|very_good",
            "main_strengths": ["..."],
            "main_weaknesses": ["..."]
        }},
        "rules": [
            {{
            "rule_id": "R01",
            "title": "short title",
            "scores": {{
                "groundedness": 1,
                "temporal_quality": 1,
                "trace_checkability": 1,
                "non_redundancy": 1,
                "ltl_translatability": 1
            }},
            "decision": "keep|rewrite|drop",
            "issues": ["..."],
            "suggested_fix": "..."
            }}
        ],
        "global_redundancies": [
            {{
            "rule_ids": ["R03", "R08"],
            "reason": "..."
            }}
        ],
        "recommended_revision_strategy": [
            "..."
        ]
        }}

        ORIGINAL CONTEXT + INSTRUCTIONS:
        -------------------------------
        {original_prompt}

        CURRENT RULE SET:
        -----------------
        {rules_json}
        """.strip()

    def _build_reviser_prompt(
            self,
            original_prompt: str,
            previous_rules,
            evaluation,
        ) -> str:
            previous_rules_json = json.dumps(previous_rules, indent=2, ensure_ascii=False)
            evaluation_json = json.dumps(evaluation, indent=2, ensure_ascii=False)

            return f"""
            You are revising a generated set of plain-English temporal safety rules
            for embodied household agents.

            Important:
            - Use the ORIGINAL CONTEXT + INSTRUCTIONS below as the only authority.
            - Use the previous rules and evaluation as feedback.
            - Do NOT assume previous rules are correct.
            - Produce a NEW FULL RULE SET FROM SCRATCH.
            - You may keep strong rules, rewrite weak rules, and drop bad ones.
            - Prefer a smaller, stronger, cleaner set over a larger noisy set.
            - Remove redundancy.
            - Avoid vague predicates unless they are explicitly grounded in the context.
            - Keep the rules interpretable and suitable for later LTL translation.

            Return ONLY valid JSON.
            Use the same output structure as the original generator:
            [
            {{
                "Rule R01: Short descriptive title": {{
                "Hazard types": ["..."],
                "Pattern family": "...",
                "Plain-English rule": "...",
                "Why it matters": "...",
                "Key trace concepts": ["..."]
                }}
            }}
            ]

            ORIGINAL CONTEXT + INSTRUCTIONS:
            -------------------------------
            {original_prompt}

            PREVIOUS RULE SET:
            ------------------
            {previous_rules_json}

            EVALUATION OF PREVIOUS RULE SET:
            --------------------------------
            {evaluation_json}
            """.strip()
            
    def generate_rules(self, prompt: str):
        rules = self._generate_json(prompt, stage="generator")
        self.history.append({"stage": "generator", "output": rules})
        return rules
    
    def evaluate_rules(self, original_prompt: str, rules):
        evaluator_prompt = self._build_evaluator_prompt(original_prompt, rules)
        evaluation = self._generate_json(evaluator_prompt, stage="evaluator")
        self.history.append({"stage": "evaluator", "output": evaluation})
        return evaluation
    
    def revise_rules(self, original_prompt: str, rules, evaluation):
        reviser_prompt = self._build_reviser_prompt(original_prompt, rules, evaluation)
        revised_rules = self._generate_json(reviser_prompt, stage="reviser")
        self.history.append({"stage": "reviser", "output": revised_rules})
        return revised_rules
    
    def run_feedback_loop(self, original_prompt: str, revision_rounds: int | None = None):
        """
        Full pipeline:
        1. Generate initial rules
        2. Evaluate them
        3. Revise them
        4. Repeat evaluator + reviser for a small number of rounds

        Returns a dictionary with all intermediate artifacts.
        """
        if revision_rounds is None:
            revision_rounds = self.max_revision_rounds

        result = {
            "initial_rules": None,
            "rounds": [],
            "final_rules": None,
        }

        print("[INFO] Starting initial rule generation...")
        rules = self.generate_rules(original_prompt)
        result["initial_rules"] = rules
        print("[INFO] Initial rule generation completed.")

        for i in range(1, revision_rounds + 1):
            print(f"[INFO] Starting revision round {i}...")

            evaluation = self.evaluate_rules(original_prompt, rules)
            print(f"[INFO] Evaluation for round {i} completed.")
            print(f"[INFO] Starting revision for round {i}...")
            revised_rules = self.revise_rules(original_prompt, rules, evaluation)
            print(f"[INFO] Revision for round {i} completed.")

            result["rounds"].append(
                {
                    "round": i,
                    "input_rules": rules,
                    "evaluation": evaluation,
                    "revised_rules": revised_rules,
                }
            )

            rules = revised_rules

        print("[INFO] Feedback loop completed.")
        result["final_rules"] = rules
        return result