from datetime import datetime
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from dotenv import load_dotenv

from english_rule_generator_agent import EnglishRuleGeneratorAgent
from generation_config import GenerationConfig

load_dotenv()

def save_outputs(output_dir: Path, rules_md: str) -> Path:
    """Save prompt and generated rules to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "rules_generated.md").write_text(rules_md, encoding="utf-8")

    return run_dir

if __name__ == "__main__":
    agent = EnglishRuleGeneratorAgent()
    
    config = GenerationConfig()
    file_contents = config.read_required_files(Path("../context"))
    final_prompt = config.build_final_prompt(file_contents)
    
    rules_md = agent.generate_rules(final_prompt)
    run_dir = save_outputs(Path("../outputs"), rules_md)
        
    print("[OK] Rule generation finished.")
    print(f"Saved files to: {run_dir}")
    print(f"Generated rules file: {run_dir / 'rules_generated.md'}")