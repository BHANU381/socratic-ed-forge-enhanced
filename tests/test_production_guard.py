import pytest
from pydantic import ValidationError
from src.models.schemas import CourseInput, LessonContract, SectionRequirement
from src.validators.markdown_validator import validate_markdown_structure
from src.validators.lesson_contract_validator import validate_lesson_contract

def test_schema_defaults():
    # 1. Missing fields should default correctly
    data = {
        "course_name": "Test Course",
        "topic": "Testing",
        "duration_weeks": 4,
        "modules": []
    }
    course = CourseInput.model_validate(data)
    assert course.learner_level == "beginner"
    assert course.code_example_style == "progressive_production"
    assert course.explanation_depth == "balanced"
    assert course.quality_profile == "standard"

    # 2. Invalid fields should raise ValidationError
    invalid_data = data.copy()
    invalid_data["learner_level"] = "expert"  # invalid!
    with pytest.raises(ValidationError):
        CourseInput.model_validate(invalid_data)

    invalid_data = data.copy()
    invalid_data["code_example_style"] = "overkill"  # invalid!
    with pytest.raises(ValidationError):
        CourseInput.model_validate(invalid_data)

    invalid_data = data.copy()
    invalid_data["explanation_depth"] = "short"  # invalid!
    with pytest.raises(ValidationError):
        CourseInput.model_validate(invalid_data)

def test_lesson_contract_validator_word_count_tolerance():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Intro", min_words=10, required=True)
        ]
    )
    
    # Target = 10 words.
    # 5 words = 50% (should be warning, not blocker)
    content_warning = "# Intro\nWord one two three four five."
    res_warning = validate_lesson_contract(content_warning, contract)
    assert res_warning.passed # because there are no blockers!
    assert len(res_warning.issues) == 1
    assert res_warning.issues[0].severity == "warning"

    # 4 words = 40% (should be blocker)
    content_blocker = "# Intro\nWord one two three."
    res_blocker = validate_lesson_contract(content_blocker, contract)
    assert not res_blocker.passed
    assert len(res_blocker.issues) == 1
    assert res_blocker.issues[0].severity == "blocker"

def test_markdown_validator_placeholders_and_leaks():
    # 1. Known mock placeholders should trigger blocker
    content = "# Introduction\nSome text here. Mocked Response is bad."
    res = validate_markdown_structure(content)
    assert not res.passed
    assert any("Mocked Response" in i.message for i in res.issues if i.severity == "blocker")

    # 2. Unresolved prompt variables should trigger blocker
    content_var = "# Introduction\nWelcome {learner_level} to our course."
    res_var = validate_markdown_structure(content_var)
    assert not res_var.passed
    assert any("learner_level" in i.message for i in res_var.issues if i.severity == "blocker")

    # 3. Empty sections should trigger blocker
    content_empty = "# Introduction\n\n# Exercises\nSome text."
    res_empty = validate_markdown_structure(content_empty)
    assert not res_empty.passed
    assert any("empty" in i.message.lower() for i in res_empty.issues if i.severity == "blocker")

def test_manifest_verification_and_export_guard(tmp_path):
    from src.engine.orchestrator import Orchestrator
    from src.models.schemas import RunManifest
    
    course = CourseInput(
        course_name="Course A",
        topic="Topic A",
        duration_weeks=4,
        modules=[
            {
                "title": "Module 1: Getting Started",
                "module_context": "Intro module",
                "submodules": [
                    {
                        "title": "1.1 Introduction",
                        "content_context": "Submodule intro"
                    }
                ]
            }
        ]
    )
    session_dir = tmp_path / "session_test"
    session_dir.mkdir()
    orch = Orchestrator(course, session_dir=session_dir)
    
    # Check extra module/submodule detection in check_manifest_and_leakage
    good_markdown = """# Table of Contents
Module 1: Getting Started
   - 1.1 Introduction
---
# Module 1: Getting Started

## Submodule: 1.1 Introduction
This is the real module content.
"""
    bad_markdown = good_markdown + "\n# Module 2: Test Module\n"
    
    # We will test checks when implemented. For now, since they are unimplemented, they will fail/raise in test.
    from src.engine.orchestrator import check_manifest_and_leakage
    err = check_manifest_and_leakage(bad_markdown, course)
    assert err is not None
    assert "extra module" in err.lower()
    
    err_good = check_manifest_and_leakage(good_markdown, course)
    assert err_good is None

    # Test verify_manifest
    manifest = RunManifest(
        session_id="test",
        course_name="Course A",
        topic="Topic A",
        duration_weeks=4,
        module_count=1,
        submodule_count=1,
        input_config_hash="abc",
        started_at="2026-06-22"
    )
    
    err_manifest = orch.verify_manifest(manifest, good_markdown)
    assert err_manifest is None
    
    # Count mismatch
    bad_count_markdown = """# Table of Contents
Module 1: Getting Started
---
# Module 1: Getting Started
"""
    err_count = orch.verify_manifest(manifest, bad_count_markdown)
    assert err_count is not None
    assert "count" in err_count.lower()

def test_clear_style_guide_on_new_run(tmp_path, monkeypatch):
    import src.utils.learning_engine as le
    
    # Mock the style guide file path to a temp file
    temp_style_guide = tmp_path / "style_guide_test.json"
    monkeypatch.setattr(le, "STYLE_GUIDE_FILE", str(temp_style_guide))
    
    # Write a dummy style guide
    temp_style_guide.write_text('{"rules": []}', encoding="utf-8")
    assert temp_style_guide.exists()
    
    # Call clear_style_guide
    from src.utils.learning_engine import clear_style_guide
    clear_style_guide()
    
    # The file should be deleted
    assert not temp_style_guide.exists()

