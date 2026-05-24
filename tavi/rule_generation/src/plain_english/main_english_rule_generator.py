from datetime import datetime
import json
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from dotenv import load_dotenv

from english_rule_generator_agent import EnglishRuleGeneratorAgent
from generation_config import GenerationConfig

load_dotenv()

def save_outputs(output_dir: Path, pipeline_result, debug_output: bool = False) -> Path:
    """Save all artifacts from the generator/evaluator/reviser pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / f"english_rules_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    def write_json(name: str, data) -> None:
        (run_dir / name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # Save initial rules
    if "initial_rules" in pipeline_result and debug_output:
        write_json("rules_v1_initial.json", pipeline_result["initial_rules"])

    # Save each round
    for round_info in pipeline_result.get("rounds", []):
        round_idx = round_info["round"]

        if "evaluation" in round_info and debug_output:
            write_json(f"evaluation_v{round_idx}.json", round_info["evaluation"])

        if "revised_rules" in round_info and debug_output:
            write_json(f"rules_v{round_idx + 1}.json", round_info["revised_rules"])

    # Save final rules
    if "final_rules" in pipeline_result:
        write_json("plain_english_rules.json", pipeline_result["final_rules"])

    # Save the whole pipeline result too
    if debug_output:
        write_json("pipeline_result.json", pipeline_result)

    return run_dir

if __name__ == "__main__":
    agent = EnglishRuleGeneratorAgent(temperature=0.4)
    
    config = GenerationConfig()
    file_contents = config.read_required_files(Path("./context"), Path("./prompts"))
    final_prompt = config.build_final_prompt(file_contents)
    
    pipeline_result = agent.run_feedback_loop(final_prompt)
    final_result = pipeline_result["final_rules"]
    
    final_rules = pipeline_result["final_rules"]

    run_dir = save_outputs(Path("./outputs"), pipeline_result, debug_output=True)
        
    print("[OK] Rule generation finished.")
    print(f"Saved files to: {run_dir}")