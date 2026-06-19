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
        "stats_passed_first_try": 5,
        "stats_passed_after_edits": 2,
        "stats_failed_max_iterations": 0
    }
    telemetry = TelemetryData.model_validate(data)
    assert telemetry.active_iterations == 2
    assert telemetry.stats_passed_first_try == 5
    assert telemetry.stats_passed_after_edits == 2
    assert telemetry.stats_failed_max_iterations == 0
