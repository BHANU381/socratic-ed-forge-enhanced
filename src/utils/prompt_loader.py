import os

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "src", "prompts")

def load_prompt(filename: str, **kwargs) -> str:
    """
    Loads a markdown prompt template from the src/prompts directory 
    and injects the provided keyword arguments.
    """
    filepath = os.path.join(PROMPTS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Prompt template '{filename}' not found at {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        template = f.read()
        
    # We use format() to inject the variables into the {placeholders}.
    # Any placeholders in the markdown not provided in kwargs will cause a KeyError.
    return template.format(**kwargs)
