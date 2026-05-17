from pathlib import Path
import textwrap
from typing import Dict, List

REQUIRED_FILES = [
    "ai2thor_actions.md",
    "ai2thor_object_states.md",
    "hazards_types.md",
    "ltl_patterns.md",
    "rule_generation_prompt.md",
]

class GenerationConfig:
    
    @staticmethod
    def read_required_files(context_dir: Path) -> Dict[str, str]:
        """Read all required markdown files from the context directory."""
        contents: Dict[str, str] = {}

        missing: List[str] = []
        for filename in REQUIRED_FILES:
            path = context_dir / filename
            if not path.exists():
                missing.append(str(path))
                continue
            contents[filename] = path.read_text(encoding="utf-8")

        if missing:
            joined = "\n".join(f"  - {m}" for m in missing)
            raise FileNotFoundError(
                "The following required files are missing:\n"
                f"{joined}"
            )

        return contents
    
    @staticmethod
    def build_final_prompt(file_contents: Dict[str, str]) -> str:
        """
        Build the final prompt given to Gemini.

        The prompt template lives in rule_generation_prompt.md.
        We append the remaining files as authoritative context documents.
        """
        base_prompt = file_contents["rule_generation_prompt.md"].strip()

        context_sections = []
        for filename in REQUIRED_FILES:
            if filename == "rule_generation_prompt.md":
                continue
            body = file_contents[filename].strip()
            section = f"## Begin context file: {filename}\n\n{body}\n\n## End context file: {filename}"
            context_sections.append(section)

        joined_context = "\n\n".join(context_sections)

        final_prompt = textwrap.dedent(
            f"""\
            {base_prompt}

            ---

            Below are the authoritative context documents you must use.

            {joined_context}

            ---

            Generate the final curated rule list now.
            """
        ).strip()

        return final_prompt