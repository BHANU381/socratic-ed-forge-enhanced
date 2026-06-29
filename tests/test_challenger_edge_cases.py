import pytest
import json
from pydantic import ValidationError
from src.models.schemas import CourseInput, Module, Submodule
import src.engine.orchestrator as orchestrator
from unittest.mock import patch

def test_missing_prompt_theme_fallback():
    """Verify prompt_theme falls back to 'default' when missing."""
    data = {
        "course_name": "Test Course",
        "topic": "Test Topic",
        "duration_weeks": 4,
        "modules": []
    }
    course = CourseInput.model_validate(data)
    assert course.prompt_theme == "default"

def test_missing_modules_fallback():
    """Verify modules list falls back to empty list when missing."""
    data = {
        "course_name": "Test Course",
        "topic": "Test Topic",
        "duration_weeks": 4
    }
    course = CourseInput.model_validate(data)
    assert course.modules == []

def test_missing_submodules_fallback():
    """Verify submodules list in Module falls back to empty list when missing."""
    data = {
        "title": "Module Title",
        "module_context": "Module Context"
    }
    mod = Module.model_validate(data)
    assert mod.submodules == []

def test_empty_strings_validation():
    """Verify that empty strings for course_name, topic, etc. are parsed without validation errors."""
    data = {
        "course_name": "",
        "topic": "",
        "duration_weeks": 0,
        "modules": []
    }
    course = CourseInput.model_validate(data)
    assert course.course_name == ""
    assert course.topic == ""
    assert course.duration_weeks == 0

def test_graceful_missing_fields_validation_error():
    """Verify missing required fields raise ValidationError."""
    data = {
        "course_name": "Only Name"
    }
    with pytest.raises(ValidationError) as exc:
        CourseInput.model_validate(data)
    assert "topic" in str(exc.value)
    assert "duration_weeks" in str(exc.value)

@patch("builtins.print")
def test_orchestrator_handles_missing_file_gracefully(mock_print, tmp_path, monkeypatch):
    """Verify orchestrator prints error and returns gracefully when course_input.json is missing."""
    # Point PROJECT_ROOT to tmp_path
    monkeypatch.setattr(orchestrator, "PROJECT_ROOT", tmp_path)
    
    # Run main, should not raise exception
    orchestrator.main()
    
    # Assert printing the file not found message
    any_file_not_found_msg = any("Input file not found" in call[0][0] for call in mock_print.call_args_list)
    assert any_file_not_found_msg

@patch("builtins.print")
def test_orchestrator_handles_malformed_json_gracefully(mock_print, tmp_path, monkeypatch):
    """Verify orchestrator prints error and returns gracefully when course_input.json is malformed JSON."""
    # Point PROJECT_ROOT to tmp_path
    monkeypatch.setattr(orchestrator, "PROJECT_ROOT", tmp_path)
    
    data_dir = tmp_path / 'data' / 'input'
    data_dir.mkdir(parents=True)
    input_file = data_dir / 'course_input.json'
    input_file.write_text("invalid json content")
    
    # Run main, should not raise exception
    orchestrator.main()
    
    # Assert printing the invalid JSON message
    any_invalid_json_msg = any("invalid JSON" in call[0][0] for call in mock_print.call_args_list)
    assert any_invalid_json_msg

@patch("builtins.print")
def test_orchestrator_handles_validation_failure_gracefully(mock_print, tmp_path, monkeypatch):
    """Verify orchestrator prints error and returns gracefully when schema validation fails."""
    # Point PROJECT_ROOT to tmp_path
    monkeypatch.setattr(orchestrator, "PROJECT_ROOT", tmp_path)
    
    data_dir = tmp_path / 'data' / 'input'
    data_dir.mkdir(parents=True)
    input_file = data_dir / 'course_input.json'
    # invalid schema (missing course_name)
    input_file.write_text(json.dumps({
        "topic": "Testing",
        "modules": []
    }))
    
    # Run main, should not raise exception
    orchestrator.main()
    
    # Assert printing the validation failed message
    any_val_fail_msg = any("Schema Validation Failed" in call[0][0] for call in mock_print.call_args_list)
    assert any_val_fail_msg
