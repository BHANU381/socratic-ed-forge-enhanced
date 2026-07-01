import os
from typing import Tuple, List

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "src", "prompts")

def load_prompt(filename: str, theme: str = "default", **kwargs) -> Tuple[str, List[str]]:
    """
    Loads a markdown prompt template from the src/prompts/{theme} directory 
    and injects the provided keyword arguments.
    Returns (prompt_text, required_headings).
    """
    # Prevent path traversal implicitly by basic check (though pydantic catches it earlier at API level,
    # this protects direct python calls)
    if ".." in theme or "/" in theme or "\\" in theme:
        raise ValueError(f"Invalid theme name: {theme}")

    theme_dir = os.path.join(PROMPTS_DIR, theme)
    filepath = os.path.join(theme_dir, filename)
    
    if not os.path.exists(filepath):
        default_filepath = os.path.join(PROMPTS_DIR, "default", filename)
        if os.path.exists(default_filepath):
            filepath = default_filepath
        else:
            raise FileNotFoundError(f"Prompt template '{filename}' not found in theme '{theme}' at {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        template = f.read()
        
    required_headings = []
    # Check for validation block
    if "### VALIDATION RULES" in template and "------------------------------------------------------------" in template:
        parts = template.split("------------------------------------------------------------\n", 1)
        if len(parts) == 2:
            rules_block = parts[0]
            template = parts[1] # Strip the block out
            
            # Extract lines starting with "- "
            for line in rules_block.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    required_headings.append(line[2:].strip())

    # We use format() to inject the variables into the {placeholders}.
    # Any placeholders in the markdown not provided in kwargs will cause a KeyError.
    kwargs.setdefault("tool_stack", "Tools: None\nTech Stack: None")
    kwargs.setdefault("grounding_context", "Grounding Context: Empty")
    return template.format(**kwargs), required_headings
