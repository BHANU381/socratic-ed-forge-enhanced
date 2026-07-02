import pytest
from pydantic import ValidationError
from src.models.schemas import CourseStructure

def get_valid_payload():
    return {
        "course_title": "Production-Ready Backend Engineering",
        "course_context": "A practical course on backend development.",
        "modules": [
            {
                "module_title": "Module 1",
                "module_context": "Introduction context",
                "topics": [
                    {
                        "topic_title": "Topic 1",
                        "concept": "Core topic concept"
                    }
                ]
            }
        ]
    }

def test_optional_string_as_null():
    payload = get_valid_payload()
    # Add null values to optional string fields
    payload["modules"][0]["topics"][0]["constraints"] = None
    payload["modules"][0]["topics"][0]["edge_cases"] = None
    payload["modules"][0]["topics"][0]["expert_heuristic"] = None
    
    # Should validate successfully
    course = CourseStructure.model_validate(payload)
    assert course.modules[0].topics[0].constraints == ""

def test_optional_string_as_empty_string():
    payload = get_valid_payload()
    payload["modules"][0]["topics"][0]["constraints"] = ""
    payload["modules"][0]["topics"][0]["edge_cases"] = ""
    
    course = CourseStructure.model_validate(payload)
    assert course.modules[0].topics[0].constraints == ""

def test_optional_list_as_null():
    payload = get_valid_payload()
    payload["modules"][0]["topics"][0]["action_items"] = None
    payload["modules"][0]["topics"][0]["common_mistakes"] = None
    
    course = CourseStructure.model_validate(payload)
    assert course.modules[0].topics[0].action_items == []
    assert course.modules[0].topics[0].common_mistakes == []

def test_optional_list_as_empty_list():
    payload = get_valid_payload()
    payload["modules"][0]["topics"][0]["action_items"] = []
    payload["modules"][0]["topics"][0]["common_mistakes"] = []
    
    course = CourseStructure.model_validate(payload)
    assert course.modules[0].topics[0].action_items == []

def test_missing_required_course_context():
    payload = get_valid_payload()
    del payload["course_context"]
    
    with pytest.raises(ValidationError) as exc_info:
        CourseStructure.model_validate(payload)
    assert "course_context" in str(exc_info.value)

def test_missing_required_module_context():
    payload = get_valid_payload()
    del payload["modules"][0]["module_context"]
    
    with pytest.raises(ValidationError) as exc_info:
        CourseStructure.model_validate(payload)
    assert "module_context" in str(exc_info.value)

def test_required_field_as_null():
    payload = get_valid_payload()
    payload["course_context"] = None
    
    with pytest.raises(ValidationError) as exc_info:
        CourseStructure.model_validate(payload)
    assert "course_context" in str(exc_info.value)

def test_unexpected_field_rejection():
    payload = get_valid_payload()
    payload["unexpected_config_field"] = "unexpected"
    
    with pytest.raises(ValidationError) as exc_info:
        CourseStructure.model_validate(payload)
    assert "extra" in str(exc_info.value) or "unexpected_config_field" in str(exc_info.value)

def test_grounding_fields_parsing():
    payload = get_valid_payload()
    payload["course_material_ids"] = ["chunk_1", "chunk_2"]
    payload["material_bank"] = {"chunk_1": "Content 1"}
    payload["tool_stack"] = {
        "tools": ["python", "pip"],
        "tech_stack": ["FastAPI"]
    }
    payload["modules"][0]["module_material_ids"] = ["mod_chunk_1"]
    payload["modules"][0]["topics"][0]["topic_material_ids"] = ["top_chunk_1"]
    
    course = CourseStructure.model_validate(payload)
    assert course.course_material_ids == ["chunk_1", "chunk_2"]
    assert course.material_bank["chunk_1"] == "Content 1"
    assert course.tool_stack.tools == ["python", "pip"]
    assert course.modules[0].module_material_ids == ["mod_chunk_1"]
    assert course.modules[0].topics[0].topic_material_ids == ["top_chunk_1"]

def test_grounding_fields_missing():
    payload = get_valid_payload()
    # Missing all grounding fields entirely
    course = CourseStructure.model_validate(payload)
    assert course.course_material_ids == []
    assert course.tool_stack is None
