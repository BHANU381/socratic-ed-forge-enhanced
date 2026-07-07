import pytest
import os
import re
from pathlib import Path

# Extract expected kwargs from core.py manually or dynamically.
# For simplicity, we hardcode the expected kwargs for each agent based on core.py's implementation.

EXPECTED_KWARGS = {
    "archivist.md": {"course_name", "course_topic", "duration_weeks", "sub_title", "submodule_title", "content_context", "module_context", "feedback", "critic_feedback", "learning_context_block", "draft", "lesson_draft", "module_title", "running_summary", "source_context", "learned_rules", "approved_lesson", "module_id", "submodule_id", "content"},
    "content_generator.md": {"course_name", "course_topic", "duration_weeks", "module_title", "sub_title", "submodule_title", "content_context", "module_context", "running_summary", "learned_rules", "source_context", "learning_context_block", "lesson_contract", "quality_profile", "learner_level", "code_example_style", "explanation_depth", "module_position", "learner_level_rules", "core_idea_words", "implementation_words", "why_it_matters_words", "breakdown", "topic_constraints", "edge_cases", "action_items", "common_mistakes", "expert_heuristic", "evaluation_path", "tool_stack", "grounding_context", "concept", "student_personas"},
    "semantic_evaluator.md": {"draft", "lesson_contract", "course_topic", "submodule_title", "running_summary", "learner_level", "code_example_style", "explanation_depth", "module_position", "breakdown", "topic_constraints", "edge_cases", "action_items", "common_mistakes", "expert_heuristic", "evaluation_path", "student_personas"},
    "patch_editor.md": {"draft", "feedback", "heading", "course_topic", "submodule_title", "learner_level", "patch_mode", "issues", "lesson_contract", "running_summary", "breakdown", "topic_constraints", "edge_cases", "action_items", "common_mistakes", "expert_heuristic", "evaluation_path", "grounding_context", "student_personas"},
    "grounding_faithfulness_auditor.md": {"content", "course_context", "module_context", "topic_context", "tool_stack", "grounding_context"},
    "style_synthesizer_rule.md": {"critique", "correction"},
    "style_synthesizer_duplicate.md": {"rules_formatted", "new_rule"}
}

def get_all_prompts():
    """Yields (theme, filename, filepath) for every .md file in src/prompts/"""
    project_root = Path(__file__).resolve().parent.parent.parent
    prompts_dir = project_root / "src" / "prompts"
    
    for theme_dir in prompts_dir.iterdir():
        if theme_dir.is_dir() and not theme_dir.name.startswith("."):
            for prompt_file in theme_dir.glob("*.md"):
                # Ignore SOPs or non-agent markdown files
                if prompt_file.name == "PROMPT_THEMING_SOP.md":
                    continue
                yield theme_dir.name, prompt_file.name, prompt_file

@pytest.mark.parametrize("theme, filename, filepath", list(get_all_prompts()))
def test_prompt_variables_match_kwargs(theme, filename, filepath):
    """
    Reads the prompt markdown and ensures every {variable} used is 
    in the expected kwargs list for that specific agent.
    """
    content = filepath.read_text(encoding="utf-8")
    
    # Regex to find all {variables} in the markdown. 
    # Ignores JSON-like double braces {{ }} if any exist.
    # We use a negative lookbehind and lookahead to skip {{ and }}
    variables = set(re.findall(r'(?<!\{)\{([a-zA-Z_]+)\}(?!\})', content))
    
    # Check if the filename is known
    assert filename in EXPECTED_KWARGS, f"Unknown prompt file '{filename}' found in theme '{theme}'. Update EXPECTED_KWARGS in this test if this is a new agent."
    
    expected_vars = EXPECTED_KWARGS[filename]
    
    # Find any variables in the markdown that are NOT in the expected kwargs
    missing_kwargs = variables - expected_vars
    
    assert not missing_kwargs, (
        f"\n[FAIL] Prompt '{filename}' in theme '{theme}' uses variables that are not passed by Python: {missing_kwargs}\n"
        f"Variables found in markdown: {variables}\n"
        f"Variables expected from Python: {expected_vars}"
    )
