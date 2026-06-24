import pytest
from src.utils.prompt_loader import load_prompt

def test_guided_weekly_content_generator():
    """Verify that guided_weekly content_generator prompt expects guided_weekly variables."""
    # Dummy kwargs required by content_generator
    dummy_kwargs = {
        "course_name": "Test Course",
        "course_topic": "Test Topic",
        "duration_weeks": "4",
        "module_title": "Module 1",
        "sub_title": "sub_title",
        "submodule_title": "1.1 Introduction",
        "content_context": "Explain stuff",
        "module_context": "Module context here",
        "running_summary": "Previous stuff",
        "learned_rules": "",
        "source_context": "",
        "learning_context_block": "",
        "lesson_contract": "contract data",
        "quality_profile": "standard",
        "learner_level": "beginner",
        "code_example_style": "simple",
        "explanation_depth": "deep",
        "module_position": "start",
        "learner_level_rules": "No complex stuff"
    }
    
    content, headings = load_prompt("content_generator.md", theme="guided_weekly", **dummy_kwargs)
    
    assert "Learning Target" in content
    assert "Where This Fits" in content
    assert "VALIDATION RULES" not in content

def test_guided_weekly_semantic_evaluator():
    dummy_kwargs = {
        "course_topic": "Test Topic",
        "submodule_title": "1.1 Introduction",
        "learner_level": "beginner",
        "code_example_style": "simple",
        "explanation_depth": "deep",
        "module_position": "start",
        "lesson_contract": "contract data",
        "running_summary": "summary",
        "draft": "draft content"
    }
    content, _ = load_prompt("semantic_evaluator.md", theme="guided_weekly", **dummy_kwargs)
    assert "Learning Target" in content
    assert "Worked Example" in content

def test_guided_weekly_patch_editor():
    dummy_kwargs = {
        "draft": "draft",
        "issues": "issues list",
        "submodule_title": "1.1",
        "course_topic": "topic",
        "lesson_contract": "contract",
        "running_summary": "summary",
        "learner_level": "beginner",
        "patch_mode": "strict",
        "heading": "heading",
        "feedback": "feedback"
    }
    content, _ = load_prompt("patch_editor.md", theme="guided_weekly", **dummy_kwargs)
    assert "Patch Editor" in content
    assert "issues list" in content

def test_guided_weekly_archivist():
    dummy_kwargs = {
        "course_name": "Test Course",
        "course_topic": "Test Topic",
        "duration_weeks": "4",
        "sub_title": "sub",
        "submodule_title": "sub",
        "content_context": "context",
        "module_context": "context",
        "feedback": "feedback",
        "critic_feedback": "feedback",
        "learning_context_block": "context",
        "draft": "draft",
        "lesson_draft": "draft",
        "module_title": "module",
        "running_summary": "summary",
        "source_context": "source",
        "learned_rules": "rules",
        "approved_lesson": "lesson",
        "module_id": "1",
        "submodule_id": "1",
        "content": "Full content of submodule"
    }
    content, _ = load_prompt("archivist.md", theme="guided_weekly", **dummy_kwargs)
    assert "Full content" in content
