import pytest
from pydantic import ValidationError
from src.models.schemas import CourseInput, Module, Submodule

def test_valid_payload():
    """Happy Path: valid JSON strictly maps to the models."""
    data = {
        "course_name": "Harness Engineering for Beginners",
        "topic": "A beginner-friendly course on designing reliable AI agent systems.",
        "duration_weeks": 6,
        "modules": [
            {
                "title": "Module 1",
                "module_context": "Introduction",
                "submodules": [
                    {
                        "title": "1.1 Model vs Harness",
                        "content_context": "Explain the difference"
                    }
                ]
            }
        ]
    }
    
    course = CourseInput.model_validate(data)
    assert course.course_name == "Harness Engineering for Beginners"
    assert course.duration_weeks == 6
    assert len(course.modules) == 1
    assert len(course.modules[0].submodules) == 1
    assert course.modules[0].submodules[0].title == "1.1 Model vs Harness"

def test_missing_required_field():
    """Edge Case: Missing duration_weeks raises ValidationError."""
    data = {
        "course_name": "Test",
        "topic": "Test topic",
        # "duration_weeks": missing!
        "modules": []
    }
    with pytest.raises(ValidationError) as exc_info:
        CourseInput.model_validate(data)
    
    # Check that the error explicitly mentions the missing duration_weeks field
    assert "duration_weeks" in str(exc_info.value)

def test_type_mismatch():
    """Edge Case: Providing a string instead of an int for duration_weeks."""
    data = {
        "course_name": "Test",
        "topic": "Test topic",
        "duration_weeks": "six",  # should be int
        "modules": []
    }
    with pytest.raises(ValidationError) as exc_info:
        CourseInput.model_validate(data)
    
    assert "duration_weeks" in str(exc_info.value)

def test_empty_lists():
    """Edge Case: Ensure empty modules array parses properly but respects the schema."""
    data = {
        "course_name": "Test",
        "topic": "Test topic",
        "duration_weeks": 4,
        "modules": []
    }
    course = CourseInput.model_validate(data)
    assert course.modules == []

def test_invalid_prompt_theme():
    """Edge Case: prompt_theme must match regex ^[a-zA-Z0-9_-]+$"""
    data = {
        "course_name": "Test",
        "topic": "Test topic",
        "duration_weeks": 4,
        "modules": [],
        "prompt_theme": "../invalid"
    }
    with pytest.raises(ValidationError) as exc_info:
        CourseInput.model_validate(data)
    assert "prompt_theme" in str(exc_info.value)

def test_telemetry_loop_stats():
    """Test that TelemetryData accepts new generation loop stats."""
    from src.models.schemas import TelemetryData
    data = {
        "status": "Running",
        "progress_percent": 50,
        "current_agent": "Editor",
        "total_tokens": 1000,
        "input_tokens": 800,
        "output_tokens": 200,
        "model_name": "gemini-1.5-pro",
        "current_module": "Module 1",
        "current_submodule": "1.1",
        "active_iterations": 2,
        "passed_1st_iteration": 5,
        "passed_2nd_iteration": 2,
        "passed_3rd_iteration": 0,
        "failed_max_iterations": 0
    }
    telemetry = TelemetryData.model_validate(data)
    assert telemetry.active_iterations == 2
    assert telemetry.passed_1st_iteration == 5
    assert telemetry.passed_2nd_iteration == 2
    assert telemetry.passed_3rd_iteration == 0
    assert telemetry.failed_max_iterations == 0

def test_new_refactor_schemas():
    """TDD Test: Verify importing and validating new schemas for the general-purpose course engine."""
    from src.models.schemas import (
        ValidationIssue,
        ValidationResult,
        SectionRequirement,
        LessonContract,
        QualityProfile,
        RunManifest
    )
    
    # Test QualityProfile enum/literal
    # QualityProfile should support light, standard, textbook
    assert QualityProfile.LIGHT == "light"
    assert QualityProfile.STANDARD == "standard"
    assert QualityProfile.TEXTBOOK == "textbook"

    # Test ValidationIssue
    issue_data = {
        "severity": "blocker",
        "issue_type": "missing_heading",
        "message": "Heading # Exercises is missing",
        "section": "Exercises"
    }
    issue = ValidationIssue.model_validate(issue_data)
    assert issue.severity == "blocker"
    assert issue.section == "Exercises"

    # Test ValidationResult
    res_data = {
        "passed": False,
        "issues": [issue_data],
        "detected_headings": ["Introduction", "Theory"]
    }
    result = ValidationResult.model_validate(res_data)
    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].severity == "blocker"

    # Test SectionRequirement and LessonContract
    contract_data = {
        "sections": [
            {
                "title": "Introduction",
                "aliases": ["Intro", "Getting Started"],
                "min_words": 50,
                "required": True
            },
            {
                "title": "Optional Details",
                "required": False
            }
        ]
    }
    contract = LessonContract.model_validate(contract_data)
    assert len(contract.sections) == 2
    assert contract.sections[0].aliases == ["Intro", "Getting Started"]
    assert contract.sections[1].required is False

    # Test TelemetryData extensions (per_agent_tokens, patch_attempts, failure_reasons)
    from src.models.schemas import TelemetryData
    telemetry_data = {
        "status": "approved",
        "progress_percent": 100,
        "current_agent": "PatchEditor",
        "total_tokens": 1500,
        "input_tokens": 1000,
        "output_tokens": 500,
        "model_name": "gemini-1.5-pro",
        "current_module": "Module 1",
        "current_submodule": "1.1",
        "per_agent_tokens": {
            "content_generator": 800,
            "semantic_evaluator": 400,
            "patch_editor": 300
        },
        "patch_attempts": 1,
        "failure_reasons": ["missing heading"]
    }
    telemetry = TelemetryData.model_validate(telemetry_data)
    assert telemetry.per_agent_tokens["content_generator"] == 800
    assert telemetry.patch_attempts == 1
    assert "missing heading" in telemetry.failure_reasons

    # Test RunManifest
    manifest_data = {
        "course_id": "course-123",
        "topic": "Python Programming",
        "lesson_contract": contract_data,
        "quality_profile": "standard",
        "completed_submodules": ["1.1", "1.2"]
    }
    manifest = RunManifest.model_validate(manifest_data)
    assert manifest.course_id == "course-123"
    assert manifest.quality_profile == "standard"
    assert len(manifest.completed_submodules) == 2

