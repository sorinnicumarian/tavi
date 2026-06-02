import json
import logging
import os
from pathlib import Path
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
        max_revision_rounds = 1,
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
            
    def _build_expander_prompt(self, original_prompt: str, rules) -> str:
        rules_json = json.dumps(rules, indent=2, ensure_ascii=False)

        return f"""
        You are a diagnostic temporal rule expansion agent for embodied household agents.

        Your job is NOT to revise the current rule set.
        Your job is NOT to output the final full rule set.
        Your job is to inspect the INITIAL DRAFT RULE SET and identify high-value missing
        diagnostic temporal rules that could improve coverage.

        Use the ORIGINAL CONTEXT + INSTRUCTIONS below as the only authority.

        Important:
        - Do not invent simulator facts.
        - Do not invent trace predicates.
        - Do not mine rules from runtime traces.
        - Do not add small variants of existing rules.
        - Do not duplicate existing rules.
        - Prefer genuinely missing temporal chains.
        - Prefer rules with clear trigger, interval, resolution, and violation condition.
        - Prefer rules that improve coverage of hazard types, temporal patterns, or trace concepts.
        - Treat your output as CANDIDATES only. A later evaluator/reviser will decide what to keep.

        The purpose of this expansion step is to answer:

        1. Which hazard types are under-covered?
        2. Which temporal pattern families are under-used?
        3. Which trace-checkable temporal chains are possible from the context but missing?
        4. Which rules would improve diagnostic value by helping locate where a safety problem started?
        5. Which rules would expose a clearer trigger -> interval -> resolution/violation structure?

        A good candidate rule should contain:

        - a clear trigger
        - a clear active interval, if applicable
        - a clear required resolution or forbidden condition
        - a clear violation condition
        - trace-checkable concepts
        - a short novelty explanation

        Return ONLY valid JSON with this structure:

        {{
        "coverage_analysis": {{
            "undercovered_hazards": [
            "..."
            ],
            "underused_pattern_families": [
            "..."
            ],
            "underused_trace_concepts": [
            "..."
            ],
            "missing_temporal_chains": [
            {{
                "chain": "trigger -> interval -> resolution/violation",
                "why_it_matters": "...",
                "likely_hazard_types": ["..."]
            }}
            ]
        }},
        "candidate_new_rules": [
            {{
            "candidate_id": "C01",
            "title": "Short descriptive title",
            "hazard_types": ["Fire"],
            "pattern_family": "Safety interval until resolution",
            "plain_english_rule": "If ...",
            "why_it_matters": "...",
            "temporal_diagnostic_structure": {{
                "trigger": "...",
                "active_interval": "...",
                "required_resolution": "...",
                "violation_condition": "...",
                "diagnostic_value": "..."
            }},
            "key_trace_concepts": [
                "added__holding__{{x}}",
                "holding__{{x}}",
                "removed__holding__{{x}}"
            ],
            "novelty_reason": "Explain why this is not redundant with the current draft.",
            "expected_value": "Explain what coverage or diagnostic value this candidate adds.",
            "risk_of_redundancy": "low|medium|high"
            }}
        ],
        "do_not_add": [
            {{
            "idea": "...",
            "reason": "Explain why this idea should not be added."
            }}
        ]
        }}

        Constraints for candidate_new_rules:

        - Generate at most 8 candidate rules.
        - Prefer 3 to 6 strong candidates over many weak ones.
        - Do not assign final rule IDs like R01, R02. Use candidate IDs C01, C02, etc.
        - Do not output LTL formulas.
        - Do not output markdown.
        - Do not include commentary outside JSON.
        - Candidate rules must be compatible with the same output philosophy as the original generator.
        - Candidate rules must be suitable for later LTL-template translation.

        ORIGINAL CONTEXT + INSTRUCTIONS:
        -------------------------------
        {original_prompt}

        INITIAL DRAFT RULE SET:
        -----------------------
        {rules_json}
        """.strip()
        
    def _build_evaluator_prompt(self, original_prompt: str, rules, expansion=None) -> str:
        rules_json = json.dumps(rules, indent=2, ensure_ascii=False)
        expansion_json = (
            json.dumps(expansion, indent=2, ensure_ascii=False)
            if expansion is not None
            else "null"
        )

        return f"""
        You are evaluating a generated set of plain-English temporal safety rules
        for embodied household agents.

        Use the ORIGINAL CONTEXT + INSTRUCTIONS below as the only authority.
        Do not invent new simulator facts.
        Do not assume the current rules are correct.
        Judge them strictly.
        
        If a rule requires unavailable trace concepts, mark it as rewrite or drop.
        The final English rule set must contain only rules that are likely expressible by the LTL translator.

        Your job:
        1. Evaluate each rule individually.
        2. Identify weak grounding, vague predicates, redundancy, poor hazard mapping,
        missing temporality, or poor trace-checkability.
        3. Produce a structured critique.
        4. Identify missing temporal-rule opportunities only if they are directly required by the current mission.
        5. When a rule is redundant, invariant-heavy, or weakly temporal, prefer dropping it.
        6. Propose a replacement rule only if the current set would otherwise miss a central mission hazard.
        7. Do not broaden coverage just to cover more hazard categories.
        8. Do not add secondary hazards unless they are clearly implied by the mission, low-level task list, or scene context.
        
        Snapshot-style rules include:
        - Global avoidance / invariant
        - Unsafe combination avoidance
        - No action while hazardous condition holds
        - formulas whose safety meaning is checked entirely within one trace step

        These rules are allowed as secondary guardrails, but they are not the main target of this project.

        When a snapshot-style rule is generated, first try to replace it with a trace-temporal version using:
        - a trigger atom such as added__...
        - a resolution atom such as removed__...
        - a before-done obligation
        - an until-safe interval

        Only keep the snapshot-style version if no faithful trace-temporal version exists.
        
        Do not treat unsafe_combination_avoidance as a temporal pattern merely because it uses G.

        A rule is genuinely temporal only if its meaning depends on relationships across multiple trace steps, such as:
        - trigger -> eventual response
        - trigger -> response before done
        - trigger -> safety condition until resolution
        - ordering / precedence over time
        - immediate next-step response

        A strong rule is not merely temporal in a generic sense. It should help explain where the safety problem started in the trace.

        For each rule, check whether it clearly identifies:
        1. the trigger step where the risky chain begins;
        2. the active interval during which the obligation or hazard remains open;
        3. the resolution/recovery event that safely closes the interval;
        4. the violation condition;
        5. the trace evidence that would let a reporter explain the failure.

        Penalize rules that are only static invariants unless the hazard is genuinely instantaneous.
        
        Scoring rubric for each rule (1 to 5):
        - groundedness
        - temporal_quality
        - trace_checkability
        - non_redundancy
        - ltl_translatability
        - diagnostic_trigger_clarity
        - active_interval_clarity
        - resolution_or_recovery_clarity
        - violation_localization_value

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
        "candidate_rules": [
            {{
                "candidate_id": "C01",
                "decision": "adopt|rewrite|reject",
                "reason": "...",
                "suggested_revision": "..."
            }}
        ]
        "global_redundancies": [
            {{
            "rule_ids": ["R03", "R08"],
            "reason": "..."
            }}
        ],
        "recommended_revision_strategy": [
            "..."
        ],
        "missing_temporal_opportunities": [
            {{
                "problem": "The current rules contain an invariant about electrical objects on active heat sources, but the stronger temporal version is to keep the heat source inactive until the object is removed.",
                "replacement_rule": 
                {{
                    "title": "...",
                    "hazard_types": ["..."],
                    "pattern_family": "...",
                    "plain_english_rule": "...",
                    "why_it_matters": "...",
                    "temporal_diagnostic_structure": {{
                        "trigger": "...",
                        "active_interval": "...",
                        "required_resolution": "...",
                        "violation_condition": "...",
                        "diagnostic_value": "..."
                    }},
                    "key_trace_concepts": ["..."]
                }}
            }}
        ]
        }}

        ORIGINAL CONTEXT + INSTRUCTIONS:
        -------------------------------
        {original_prompt}

        CURRENT RULE SET:
        -----------------
        {rules_json}
        
        EXPANSION CANDIDATES:
        ---------------------
        {expansion_json}
        """.strip()

    def _build_reviser_prompt(
            self,
            original_prompt: str,
            previous_rules,
            evaluation,
            expansion=None,
        ) -> str:
            previous_rules_json = json.dumps(previous_rules, indent=2, ensure_ascii=False)
            evaluation_json = json.dumps(evaluation, indent=2, ensure_ascii=False)
            expansion_json = (
                json.dumps(expansion, indent=2, ensure_ascii=False)
                if expansion is not None
                else "null"
            )

            return f"""
            You are revising a generated set of plain-English temporal safety rules
            for embodied household agents.
            
            Do not keep semantically correct but untranslatable rules.
            Rewrite them into the closest faithful rule expressible with the current trace atom vocabulary.

            Important:
            - Use the ORIGINAL CONTEXT + INSTRUCTIONS below as the only authority.
            - Use the previous rules and evaluation as feedback.
            - Do NOT assume previous rules are correct.
            - Produce a NEW FULL RULE SET FROM SCRATCH.
            - You may keep strong rules, rewrite weak rules, and drop bad ones.
            - Prefer a clean, non-redundant set over a noisy set.
           - This is online mission-conditioned rule generation, not global offline rule generation.
            - Prefer a small mission-specific rule set over broad coverage.
            - It is acceptable and often correct to shrink the rule set.
            - Do not replace every dropped rule.
            - Replace a dropped rule only if the current set would otherwise miss a central mission hazard.
            - Do not add generic household safety rules.
            - Do not add rules only to cover underrepresented hazard categories.
            - Do not add rules only to use more temporal pattern families.
            - Do not add new rules unless they are directly motivated by the current mission instruction, high-level plan, low-level task list, or explicit risk requirement.
            - The final set should normally contain around 4 to 8 strong mission-specific rules.
            - For very simple missions, 2 to 4 rules is acceptable.
            - For complex long-horizon missions, 8 to 12 rules is acceptable.
            
            Your revision is not only a filtering step.

            You must produce a stronger full rule set by:
            1. keeping good rules,
            2. rewriting weak rules,
            3. dropping truly bad or redundant rules,
            4. adding new non-redundant temporal rules suggested by the evaluation,
            5. adding a new rule only when the evaluator shows that a central mission hazard is currently uncovered,
            6. ignoring expansion candidates unless they are enabled and clearly mission-critical,
            7. rejecting expansion candidates that would only add noise or redundancy.
            
            Every revised rule should include a temporal_diagnostic_structure object.
            When rewriting a weak rule, prefer this shape:
            trigger -> monitored interval -> required resolution or forbidden event -> violation condition
            Do not output rules whose diagnostic structure is empty, vague, or only repeats the plain-English rule.
            
            The final set should normally contain around 20 to 25 strong diagnostic temporal rules.
            A rule counts as strong only if it has a clear trigger, interval/resolution, and violation-localization value, 
            unless it is explicitly justified as an instantaneous invariant.
            Do not force this number if quality would suffer, but avoid collapsing the set to only a few rules.
            
            When two rules express the same safety concern, prefer the more temporal rule.

            Example:
            - Weaker: "An electrical object must never be on an active heat source."
            - Stronger: "If an electrical object is placed on a heat source, the heat source must remain inactive until the object is removed."

            Keep the weaker invariant only if it captures a distinct safety concern not covered by the temporal rule.

            Return ONLY valid JSON.
            Use the same output structure as the original generator:
            [
                {{
                    "rule_id": "R01",
                    "title": "Short descriptive title",
                    "hazard_types": ["Fire"],
                    "pattern_family": "Safety interval until resolution",
                    "plain_english_rule": "If ...",
                    "why_it_matters": "...",
                    "key_trace_concepts": [
                    "added__holding__{{x}}",
                    "removed__holding__{{x}}"
                    ]
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
            
            EXPANSION CANDIDATES:
            ---------------------
            {expansion_json}
            """.strip()
            
    def generate_rules(self, prompt: str):
        rules = self._generate_json(prompt, stage="generator")
        self.history.append({"stage": "generator", "output": rules})
        return rules
    
    def expand_rules(self, original_prompt: str, rules):
        expander_prompt = self._build_expander_prompt(original_prompt, rules)
        expansion = self._generate_json(expander_prompt, stage="expander")
        self.history.append({"stage": "expander", "output": expansion})
        return expansion
    
    def evaluate_rules(self, original_prompt: str, rules, expansion=None):
        evaluator_prompt = self._build_evaluator_prompt(original_prompt, rules, expansion)
        evaluation = self._generate_json(evaluator_prompt, stage="evaluator")
        self.history.append({"stage": "evaluator", "output": evaluation})
        return evaluation
    
    def revise_rules(self, original_prompt: str, rules, evaluation, expansion=None):
        reviser_prompt = self._build_reviser_prompt(original_prompt, rules, evaluation, expansion)
        revised_rules = self._generate_json(reviser_prompt, stage="reviser")
        self.history.append({"stage": "reviser", "output": revised_rules})
        return revised_rules
    
    def run_feedback_loop(
    self,
    original_prompt: str,
    revision_rounds: int | None = None,
    use_expander: bool = False,
    ):
        """
        Online mission-conditioned pipeline:
        1. Generate initial mission-specific rules.
        2. Optionally expand missing candidates, disabled by default.
        3. Evaluate/audit the current rules.
        4. Revise once conservatively.

        For online generation, the expander is off by default because it tends
        to add broad global coverage instead of mission-essential rules.
        """
        if revision_rounds is None:
            revision_rounds = self.max_revision_rounds

        result = {
            "initial_rules": None,
            "initial_expansion": None,
            "rounds": [],
            "final_rules": None,
        }

        print("[INFO] Starting initial rule generation...")
        rules = self.generate_rules(original_prompt)
        result["initial_rules"] = rules
        print("[INFO] Initial rule generation completed.")

        expansion = None
        if use_expander:
            print("[INFO] Starting diagnostic rule expansion...")
            expansion = self.expand_rules(original_prompt, rules)
            result["initial_expansion"] = expansion
            print("[INFO] Diagnostic rule expansion completed.")
        else:
            print("[INFO] Skipping diagnostic rule expansion for online mission-conditioned generation.")

        for i in range(1, revision_rounds + 1):
            print(f"[INFO] Starting revision round {i}...")

            evaluation = self.evaluate_rules(original_prompt, rules, expansion)
            print(f"[INFO] Evaluation for round {i} completed.")

            print(f"[INFO] Starting conservative revision for round {i}...")
            revised_rules = self.revise_rules(original_prompt, rules, evaluation, expansion)
            print(f"[INFO] Revision for round {i} completed.")

            result["rounds"].append(
                {
                    "round": i,
                    "input_rules": rules,
                    "expansion": expansion,
                    "evaluation": evaluation,
                    "revised_rules": revised_rules,
                }
            )

            rules = revised_rules

        print("[INFO] Feedback loop completed.")
        result["final_rules"] = rules
        return result