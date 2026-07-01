import pytest
import json
import logging
from pydantic import ValidationError
from src.models.schemas import CourseStructure, normalize_course_input, Topic, ModuleStructure, ToolStack
from src.engine.grounding_resolver import resolve_grounding_context, dedupe_material_ids

# =====================================================================
# Test Group 1: Schema/default parsing
# =====================================================================

def test_schema_defaults_parsing():
    # Course JSON without tool_stack, material_bank, or material IDs still parses.
    base_input = {
        "course_title": "AI Development",
        "course_context": "Teaching AI engineering",
        "modules": [
            {
                "module_title": "Module 1",
                "module_context": "Intro module",
                "topics": [
                    {
                        "topic_title": "Topic 1.1",
                        "concept": "Topic concept"
                    }
                ]
            }
        ]
    }
    course = CourseStructure.model_validate(base_input)
    assert course.course_title == "AI Development"
    
    # Missing defaults checks
    assert course.course_material_ids == []
    assert course.material_bank == {}
    assert course.tool_stack is None or (course.tool_stack.tools == [] and course.tool_stack.tech_stack == [])
    
    assert course.modules[0].module_material_ids == []
    assert course.modules[0].topics[0].topic_material_ids == []

    # Valid tool_stack parses correctly
    stack_input = {
        "course_title": "AI Development",
        "course_context": "Teaching AI engineering",
        "tool_stack": {
            "tools": ["Git", "Terminal"],
            "tech_stack": ["React", "TypeScript"]
        },
        "modules": []
    }
    course_stack = CourseStructure.model_validate(stack_input)
    assert course_stack.tool_stack is not None
    assert course_stack.tool_stack.tools == ["Git", "Terminal"]
    assert course_stack.tool_stack.tech_stack == ["React", "TypeScript"]


# =====================================================================
# Test Group 2: Invalid input validation
# =====================================================================

def test_invalid_input_validation():
    # tool_stack.tools as string should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "tool_stack": {"tools": "Git", "tech_stack": []}, "modules": []
        })

    # tool_stack.tech_stack as string should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "tool_stack": {"tools": [], "tech_stack": "React"}, "modules": []
        })

    # course_material_ids as string should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "course_material_ids": "chunk_001", "modules": []
        })

    # module_material_ids as string should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "modules": [{
                "module_title": "M", "module_context": "C",
                "module_material_ids": "chunk_001", "topics": []
            }]
        })

    # topic_material_ids as string should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "modules": [{
                "module_title": "M", "module_context": "C",
                "topics": [{
                    "topic_title": "T", "concept": "C",
                    "topic_material_ids": "chunk_001"
                }]
            }]
        })

    # material_bank as array should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "material_bank": ["chunk_001"], "modules": []
        })

    # material_bank value as object should fail (MVP supports string only)
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "material_bank": {"chunk_001": {"text": "hello"}}, "modules": []
        })

    # material ID array containing non-string values should fail
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "course_title": "A", "course_context": "B",
            "course_material_ids": [123], "modules": []
        })


# =====================================================================
# Test Group 3: Grounding Resolver happy path
# =====================================================================

def test_grounding_resolver_happy_path():
    course_data = {
        "course_title": "AI Dev",
        "course_context": "Context",
        "course_material_ids": ["course_chunk_001"],
        "material_bank": {
            "course_chunk_001": "Course material text.",
            "module_1_chunk_001": "Module material text.",
            "topic_1_1_chunk_001": "Topic material text."
        },
        "modules": [
            {
                "module_title": "Module 1",
                "module_context": "Mod context",
                "module_material_ids": ["module_1_chunk_001"],
                "topics": [
                    {
                        "topic_title": "Topic 1.1",
                        "concept": "Topic concept",
                        "topic_material_ids": ["topic_1_1_chunk_001"]
                    }
                ]
            }
        ]
    }
    course = CourseStructure.model_validate(course_data)
    module = course.modules[0]
    topic = module.topics[0]
    
    res = resolve_grounding_context(course, module, topic)
    
    assert len(res["course_chunks"]) == 1
    assert res["course_chunks"][0]["chunk_id"] == "course_chunk_001"
    assert res["course_chunks"][0]["text"] == "Course material text."
    
    assert len(res["module_chunks"]) == 1
    assert res["module_chunks"][0]["chunk_id"] == "module_1_chunk_001"
    
    assert len(res["topic_chunks"]) == 1
    assert res["topic_chunks"][0]["chunk_id"] == "topic_1_1_chunk_001"


# =====================================================================
# Test Group 4: Deduplication hierarchy
# =====================================================================

def test_deduplication_hierarchy():
    course_data = {
        "course_title": "AI Dev",
        "course_context": "Context",
        "course_material_ids": ["chunk_001", "chunk_001"],
        "material_bank": {
            "chunk_001": "Dedupe test text."
        },
        "modules": [
            {
                "module_title": "Module 1",
                "module_context": "Mod context",
                "module_material_ids": ["chunk_001", "chunk_001"],
                "topics": [
                    {
                        "topic_title": "Topic 1.1",
                        "concept": "Topic concept",
                        "topic_material_ids": ["chunk_001", "chunk_001"]
                    }
                ]
            }
        ]
    }
    course = CourseStructure.model_validate(course_data)
    module = course.modules[0]
    topic = module.topics[0]
    
    res = resolve_grounding_context(course, module, topic)
    
    # With hierarchy: topic > module > course
    # It must be kept only in topic, and repeated elements within same array must be kept once.
    assert len(res["course_chunks"]) == 0
    assert len(res["module_chunks"]) == 0
    assert len(res["topic_chunks"]) == 1
    assert res["topic_chunks"][0]["chunk_id"] == "chunk_001"


# =====================================================================
# Test Group 5: Missing chunks
# =====================================================================

def test_missing_and_empty_chunks(caplog):
    course_data = {
        "course_title": "AI Dev",
        "course_context": "Context",
        "course_material_ids": ["chunk_valid", "chunk_missing", "chunk_empty"],
        "material_bank": {
            "chunk_valid": "Good chunk text",
            "chunk_empty": "   "
        },
        "modules": []
    }
    course = CourseStructure.model_validate(course_data)
    module = ModuleStructure(module_title="M", module_context="C", topics=[])
    topic = Topic(topic_title="T", concept="C")
    
    with caplog.at_level(logging.WARNING):
        res = resolve_grounding_context(course, module, topic)
        
    assert len(res["course_chunks"]) == 1
    assert res["course_chunks"][0]["chunk_id"] == "chunk_valid"
    
    # Check warning messages are logged
    assert any("Missing material chunk_id: chunk_missing" in record.message for record in caplog.records)
    assert any("Empty material chunk_id: chunk_empty" in record.message for record in caplog.records)


# =====================================================================
# Test Group 6: Prompt assembly
# =====================================================================

def test_prompt_assembly_injection():
    # Setup prompt inputs with tool_stack and resolved grounding
    from src.utils.prompt_loader import load_prompt
    
    dummy_kwargs = {
        "course_topic": "AI",
        "submodule_title": "Topic 1",
        "learner_level": "Beginner",
        "code_example_style": "Progressive Prod",
        "explanation_depth": "Deep",
        "module_position": "1/1",
        "lesson_contract": "Mock contract",
        "running_summary": "Mock summary",
        "breakdown": "",
        "topic_constraints": "",
        "action_items": "",
        "common_mistakes": "",
        "expert_heuristic": "",
        "evaluation_path": "",
        "sub_title": "Topic 1",
        "module_title": "Module 1",
        "learning_context_block": "",
        "edge_cases": "",
        "action_items": "",
        "common_mistakes": "",
        "expert_heuristic": "",
        "evaluation_path": "",
        "topic_constraints": "",
        "learner_level_rules": "",
        "content_context": "Concept content",
        "tool_stack": {
            "tools": ["Git"],
            "tech_stack": ["React"]
        },
        "grounding_context": {
            "course_chunks": [{"chunk_id": "c1", "text": "course content"}],
            "module_chunks": [],
            "topic_chunks": [{"chunk_id": "t1", "text": "topic content"}]
        }
    }
    
    prompt_text, _ = load_prompt("content_generator.md", theme="default", **dummy_kwargs)
    prompt_lower = prompt_text.lower()
    
    # Verify prompt contains variables and instructions
    assert "environment & grounding materials" in prompt_lower
    assert "tech_stack" in prompt_lower
    assert "grounding_context" in prompt_lower
    assert "git" in prompt_lower
    assert "react" in prompt_lower
    assert "course content" in prompt_lower
    assert "topic content" in prompt_lower
    assert "supporting source material" in prompt_lower


# =====================================================================
# Test Group 7: Backward compatibility
# =====================================================================

def test_backward_compatibility():
    legacy_input = {
        "course_name": "Legacy Course",
        "topic": "Legacy Topic",
        "duration_weeks": 2,
        "modules": [
            {
                "title": "Module 1",
                "module_context": "Context 1",
                "submodules": [
                    {
                        "title": "Topic 1.1",
                        "content_context": "Concept 1.1"
                    }
                ]
            }
        ]
    }
    
    normalized = normalize_course_input(legacy_input)
    assert normalized.course_title == "Legacy Course"
    assert normalized.course_material_ids == []
    assert normalized.material_bank == {}
    assert normalized.tool_stack is None
    
    module = normalized.modules[0]
    assert module.module_material_ids == []
    assert module.topics[0].topic_material_ids == []


# =====================================================================
# Edge Cases
# =====================================================================

def test_tool_stack_edge_cases():
    # 1. tool_stack only has tools
    ts1 = ToolStack.model_validate({"tools": ["Git"]})
    assert ts1.tools == ["Git"]
    assert ts1.tech_stack == []
    
    # 2. tool_stack only has tech_stack
    ts2 = ToolStack.model_validate({"tech_stack": ["React"]})
    assert ts2.tools == []
    assert ts2.tech_stack == ["React"]
    
    # 3. tool_stack is empty dict
    ts3 = ToolStack.model_validate({})
    assert ts3.tools == []
    assert ts3.tech_stack == []
