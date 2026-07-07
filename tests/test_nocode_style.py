import pytest
from unittest.mock import MagicMock
from src.models.schemas import CourseStructure
from src.engine.orchestrator import Orchestrator

def test_nocode_schema_acceptance():
    payload = {
        "course_title": "No-Code Cloud Basics",
        "course_context": "Cloud architecture without code",
        "prompt_theme": "otto2_structured",
        "code_example_style": "none",
        "modules": []
    }
    course = CourseStructure(**payload)
    assert course.code_example_style == "none"

def test_nocode_orchestrator_formatting(tmp_path):
    mock_course = MagicMock()
    mock_course.course_context = "Concept-only Course"
    mock_course.code_example_style = "none"
    mock_course.student_personas = []
    mock_course.modules = []

    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=tmp_path,
        run_type="new_run"
    )

    assert orchestrator.course.code_example_style == "none"
