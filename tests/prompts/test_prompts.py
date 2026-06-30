import pytest
import os
import tempfile
from pathlib import Path
from src.utils.prompt_loader import load_prompt

def test_prompt_loader_loads_default():
    """Validates that passing theme='default' successfully loads a template."""
    # This assumes 'content_generator.md' exists in src/prompts/default/
    content, headings = load_prompt("content_generator.md", theme="default", sub_title="test", course_name="test", course_topic="test", duration_weeks="test", module_title="test", submodule_title="test", content_context="test", module_context="test", running_summary="test", learned_rules="test", source_context="test", learning_context_block="test", lesson_contract="test", quality_profile="test", learner_level="test", code_example_style="test", explanation_depth="test", module_position="test", learner_level_rules="test", breakdown="test", topic_constraints="test", edge_cases="test", action_items="test", common_mistakes="test", expert_heuristic="test", evaluation_path="test")
    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0
    assert isinstance(headings, list)

def test_prompt_loader_throws_on_missing_file_strict():
    """Validates that passing a custom theme missing a specific file correctly throws a FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        # We assume 'nonexistent_file.md' doesn't exist in 'default'
        load_prompt("nonexistent_file.md", theme="default")

def test_prompt_loader_path_traversal_prevention():
    """Validates that attempting to pass malicious paths to load_prompt raises an error or is blocked."""
    with pytest.raises(ValueError): # Or FileNotFoundError, but ValueError for bad theme is better
        load_prompt("editor.md", theme="../../../etc")

def test_prompt_loader_extracts_validation_rules(monkeypatch, tmp_path):
    """Validates that the loader extracts REQUIRED_HEADINGS and strips them from the prompt."""
    test_theme_dir = tmp_path / "test_theme"
    test_theme_dir.mkdir()
    test_prompt = test_theme_dir / "test_generator.md"
    
    prompt_content = """### VALIDATION RULES (SYSTEM USE ONLY - DO NOT SEND TO LLM)
REQUIRED_HEADINGS:
- ### The Hook
- ### Core Concepts Explained Simply
- ### Try It Yourself
------------------------------------------------------------
You are a helpful assistant."""
    test_prompt.write_text(prompt_content, encoding="utf-8")
    
    # Mock PROJECT_ROOT so it looks in tmp_path
    monkeypatch.setattr("src.utils.prompt_loader.PROJECT_ROOT", tmp_path.parent)
    
    # We pretend tmp_path is src/prompts
    prompt_dir = test_theme_dir.parent
    monkeypatch.setattr("src.utils.prompt_loader.PROMPTS_DIR", prompt_dir)
    
    content, headings = load_prompt("test_generator.md", theme="test_theme")
    
    assert headings == ["### The Hook", "### Core Concepts Explained Simply", "### Try It Yourself"]
    assert "VALIDATION RULES" not in content
    assert "REQUIRED_HEADINGS" not in content
    assert "You are a helpful assistant." in content

def test_semantic_evaluator_prompt_bans_word_count():
    """Validates that the semantic evaluator explicitly bans word count or length blockers."""
    # We will pass dummy strings for all the format variables
    dummy_kwargs = {
        "course_topic": "test",
        "submodule_title": "test",
        "learner_level": "test",
        "code_example_style": "test",
        "explanation_depth": "test",
        "module_position": "test",
        "lesson_contract": "test",
        "running_summary": "test",
        "draft": "test",
        "breakdown": "test",
        "topic_constraints": "test",
        "edge_cases": "test",
        "action_items": "test",
        "common_mistakes": "test",
        "expert_heuristic": "test",
        "evaluation_path": "test"
    }
    content, _ = load_prompt("semantic_evaluator.md", theme="default", **dummy_kwargs)
    
    # We expect a clear instruction prohibiting word count blockers
    assert "word count" in content.lower()
    assert "minimum words" in content.lower()
    assert "deterministic validator" in content.lower()
