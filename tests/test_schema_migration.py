import pytest
import json
from src.models.schemas import (
    CourseStructure,
    normalize_course_input,
    StudentPersona,
    Topic,
    ModuleStructure
)

def test_valid_legacy_course_normalization():
    """Verify that a valid legacy course JSON normalizes successfully into CourseStructure."""
    legacy_input = {
        "course_name": "Phase 1: AI-Assisted Software Engineering",
        "topic": "A practical beginner-to-intermediate course on AI-native software engineering.",
        "duration_weeks": 4,
        "modules": [
            {
                "title": "Block 1: Fundamentals of AI-Native Development",
                "module_context": "This module introduces AI-assisted software engineering workflows.",
                "submodules": [
                    {
                        "title": "1.1 What Is AI-Native Development?",
                        "content_context": "Explain the meaning of AI-native development and how it differs from traditional coding."
                    }
                ]
            }
        ]
    }

    normalized = normalize_course_input(legacy_input)
    assert isinstance(normalized, CourseStructure)
    assert normalized.course_title == "Phase 1: AI-Assisted Software Engineering"
    assert normalized.course_context == "A practical beginner-to-intermediate course on AI-native software engineering."
    assert normalized.duration_weeks == 4
    assert normalized.student_personas == []
    assert len(normalized.modules) == 1

    module = normalized.modules[0]
    assert isinstance(module, ModuleStructure)
    assert module.module_title == "Block 1: Fundamentals of AI-Native Development"
    assert module.module_context == "This module introduces AI-assisted software engineering workflows."
    assert module.learning_outcomes == []
    assert module.module_constraints == []
    assert len(module.topics) == 1

    topic = module.topics[0]
    assert isinstance(topic, Topic)
    assert topic.topic_title == "1.1 What Is AI-Native Development?"
    assert topic.concept == "Explain the meaning of AI-native development and how it differs from traditional coding."
    assert topic.breakdown == ""
    assert topic.constraints == ""
    assert topic.edge_cases == ""
    assert topic.action_items == []
    assert topic.common_mistakes == []
    assert topic.evaluation_path == ""
    assert topic.expert_heuristic == ""
    assert topic.reference_guides is None
    assert topic.expert_story is None

def test_minimal_legacy_input_success():
    """Verify that a minimal valid legacy input successfully normalizes and fills defaults."""
    minimal_input = {
        "course_name": "Example Course",
        "topic": "This course teaches the core ideas of the topic.",
        "modules": [
            {
                "title": "Module 1: Foundations",
                "module_context": "This module introduces the foundations.",
                "submodules": [
                    {
                        "title": "1.1 Introduction",
                        "content_context": "This topic introduces the main idea."
                    }
                ]
            }
        ]
    }

    normalized = normalize_course_input(minimal_input)
    assert normalized.course_title == "Example Course"
    assert normalized.course_context == "This course teaches the core ideas of the topic."
    assert normalized.duration_weeks is None
    assert normalized.student_personas == []
    assert len(normalized.modules) == 1

    module = normalized.modules[0]
    assert module.module_title == "Module 1: Foundations"
    assert module.module_context == "This module introduces the foundations."
    assert len(module.topics) == 1

    topic = module.topics[0]
    assert topic.topic_title == "1.1 Introduction"
    assert topic.concept == "This topic introduces the main idea."
    assert topic.breakdown == ""
    assert topic.reference_guides is None

@pytest.mark.parametrize("missing_field, payload_modifier", [
    ("course_name", lambda p: p.pop("course_name")),
    ("topic", lambda p: p.pop("topic")),
    ("modules", lambda p: p.pop("modules")),
    ("modules[0].title", lambda p: p["modules"][0].pop("title")),
    ("modules[0].module_context", lambda p: p["modules"][0].pop("module_context")),
    ("modules[0].submodules", lambda p: p["modules"][0].pop("submodules")),
    ("modules[0].submodules[0].title", lambda p: p["modules"][0]["submodules"][0].pop("title")),
    ("modules[0].submodules[0].content_context", lambda p: p["modules"][0]["submodules"][0].pop("content_context")),
])
def test_required_field_validations(missing_field, payload_modifier):
    """Verify that missing required legacy fields fail with clear path-specific error messages."""
    base_input = {
        "course_name": "Example",
        "topic": "Example Topic",
        "modules": [
            {
                "title": "M1",
                "module_context": "M1 context",
                "submodules": [
                    {
                        "title": "S1",
                        "content_context": "S1 context"
                    }
                ]
            }
        ]
    }
    payload_modifier(base_input)

    with pytest.raises(ValueError) as excinfo:
        normalize_course_input(base_input)
    assert missing_field in str(excinfo.value)
    assert "required" in str(excinfo.value).lower()

def test_tutor_wrapper_rejection():
    """Verify that a wrapped tutor format input fails with a clear message."""
    tutor_input = {
        "tutor": {
            "course_structure": {
                "course_title": "Example Course"
            }
        }
    }
    with pytest.raises(ValueError) as excinfo:
        normalize_course_input(tutor_input)
    assert "Do not pass tutor.course_structure" in str(excinfo.value)

def test_root_level_new_format_acceptance():
    """Verify that passing the new format directly at root level succeeds."""
    new_format_input = {
        "course_title": "Example Course",
        "course_context": "Example Context",
        "modules": []
    }
    res = normalize_course_input(new_format_input)
    assert res.course_title == "Example Course"
    assert res.course_context == "Example Context"

def test_removed_fields_ignored_safely():
    """Verify that removed fields are not required and are ignored safely without errors."""
    input_with_removed_fields = {
        "course_name": "Example Course",
        "topic": "This course teaches the core ideas of the topic.",
        "instructional_material_hours": 10,
        "modules": [
            {
                "title": "Module 1: Foundations",
                "module_context": "This module introduces the foundations.",
                "module_instructional_hours": 2,
                "module_goal": "Teach basics",
                "submodules": [
                    {
                        "title": "1.1 Introduction",
                        "content_context": "This topic introduces the main idea.",
                        "topic_instructional_hours": 1,
                        "inferred": True,
                        "inference_rationale": "testing"
                    }
                ]
            }
        ]
    }
    normalized = normalize_course_input(input_with_removed_fields)
    assert normalized.course_title == "Example Course"
    # Ensure they don't crash and are simply ignored
    assert not hasattr(normalized, "instructional_material_hours")
    assert not hasattr(normalized.modules[0], "module_instructional_hours")
    assert not hasattr(normalized.modules[0], "module_goal")
    assert not hasattr(normalized.modules[0].topics[0], "topic_instructional_hours")
    assert not hasattr(normalized.modules[0].topics[0], "inferred")

def test_reference_guides_defaults_and_grounding():
    """Verify that reference_guides defaults to null and does not trigger errors."""
    legacy_input = {
        "course_name": "Example Course",
        "topic": "This course teaches the core ideas of the topic.",
        "modules": [
            {
                "title": "Module 1",
                "module_context": "Context",
                "submodules": [
                    {
                        "title": "1.1",
                        "content_context": "Concept content"
                    }
                ]
            }
        ]
    }
    normalized = normalize_course_input(legacy_input)
    assert normalized.modules[0].topics[0].reference_guides is None
