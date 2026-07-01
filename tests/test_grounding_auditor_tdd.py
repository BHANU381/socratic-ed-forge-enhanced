import pytest
import json
from pydantic import ValidationError
from src.models.schemas import CourseStructure, normalize_course_input, Topic, ModuleStructure
from src.engine.grounding_resolver import resolve_grounding_context
from src.engine.orchestrator import check_manifest_and_leakage
from src.validators.markdown_validator import validate_markdown_structure

# =====================================================================
# Test Group 1: Long chunk parsing & grounding resolver
# =====================================================================

def test_long_chunk_parsing_and_resolver():
    # material_bank accepts a multi-paragraph chunk with markdown bullets/code.
    long_chunk_content = """### Dynamic RAG Grounding
This is a long paragraph explaining grounding.
* Bullet 1: Detail A
* Bullet 2: Detail B

```python
# Code example
print("Hello RAG")
```
"""
    course_input = {
        "course_title": "Long Chunk Course",
        "course_context": "Deep Dive",
        "course_material_ids": ["c1"],
        "material_bank": {
            "c1": long_chunk_content
        },
        "modules": []
    }
    
    course = CourseStructure.model_validate(course_input)
    assert course.material_bank["c1"] == long_chunk_content
    
    # Grounding resolver preserves paragraphs and code fences
    module = ModuleStructure(module_title="M", module_context="C", topics=[])
    topic = Topic(topic_title="T", concept="C")
    
    res = resolve_grounding_context(course, module, topic)
    assert len(res["course_chunks"]) == 1
    resolved_text = res["course_chunks"][0]["text"]
    assert resolved_text == long_chunk_content
    assert "```python" in resolved_text
    assert "* Bullet 1" in resolved_text


# =====================================================================
# Test Group 2: Context-aware placeholder blocking & template slots
# =====================================================================

def test_placeholder_blocking_rules():
    # Unfinished authoring placeholders must fail
    content_todo = """#### Core Idea
[TODO]
"""
    res = validate_markdown_structure(content_todo)
    assert any(i.severity == "blocker" and i.issue_type == "placeholder" for i in res.issues)

    content_insert = """#### Implementation
[Insert implementation here]
"""
    res = validate_markdown_structure(content_insert)
    assert any(i.severity == "blocker" and i.issue_type == "placeholder" for i in res.issues)

    content_add = """#### Why it Matters
[Add example later]
"""
    res = validate_markdown_structure(content_add)
    assert any(i.severity == "blocker" and i.issue_type == "placeholder" for i in res.issues)


def test_learner_template_placeholder_allowance():
    # Pass inside template block context
    content_valid_template = """**Prompt template**

The command failed:

[PASTE THE COMMAND THAT FAILED HERE]

The terminal output was:

[PASTE 3-5 LINES OF THE ACTUAL TERMINAL ERROR HERE]
"""
    res = validate_markdown_structure(content_valid_template)
    # Filter for blockers
    blockers = [i for i in res.issues if i.severity == "blocker"]
    assert len(blockers) == 0

    content_valid_diagnostic = """**Diagnostic prompt**

In `src/components/UserDashboard.tsx`, I expected [EXPECTED BEHAVIOR], but observed [ACTUAL BEHAVIOR].
"""
    res = validate_markdown_structure(content_valid_diagnostic)
    blockers = [i for i in res.issues if i.severity == "blocker"]
    assert len(blockers) == 0

    # Fail outside template context
    content_invalid_outside = """#### Implementation

[EXPECTED BEHAVIOR]
"""
    res = validate_markdown_structure(content_invalid_outside)
    blockers = [i for i in res.issues if i.severity == "blocker"]
    assert len(blockers) > 0


# =====================================================================
# Test Group 3: Regression test for current failure
# =====================================================================

def test_regression_bracket_error_context():
    # The exact lowercase format from the current run
    bracket_text = "[Insert 3-5 lines of specific terminal error]"
    
    # 1. Inside template context -> Allowed
    content_inside = f"""**Diagnostic prompt template**

{bracket_text}
"""
    res_inside = validate_markdown_structure(content_inside)
    blockers_inside = [i for i in res_inside.issues if i.severity == "blocker"]
    assert len(blockers_inside) == 0

    # 2. Outside template context -> Blocked
    content_outside = f"""#### Why it Matters

{bracket_text}
"""
    res_outside = validate_markdown_structure(content_outside)
    blockers_outside = [i for i in res_outside.issues if i.severity == "blocker"]
    assert len(blockers_outside) > 0


# =====================================================================
# Test Group 4: Auditor & Validator consistency
# =====================================================================

def test_validator_and_export_guard_consistency():
    course_input = {
        "course_title": "Test",
        "course_context": "Test",
        "modules": []
    }
    course = CourseStructure.model_validate(course_input)

    # Both block same unresolved placeholders
    content = """#### Implementation
[TODO]
"""
    res_val = validate_markdown_structure(content)
    blockers_val = [i for i in res_val.issues if i.severity == "blocker"]
    assert len(blockers_val) > 0
    
    res_guard = check_manifest_and_leakage(content, course)
    assert res_guard is not None
    assert "TODO" in res_guard

    # Both allow template slots
    content_temp = """**Prompt template**
[EXPECTED BEHAVIOR]
"""
    res_val = validate_markdown_structure(content_temp)
    blockers_val = [i for i in res_val.issues if i.severity == "blocker"]
    assert len(blockers_val) == 0
    
    res_guard = check_manifest_and_leakage(content_temp, course)
    assert res_guard is None


# =====================================================================
# Test Group 5: GroundingFaithfulnessAuditor Agent Direct Tests
# =====================================================================

def test_grounding_auditor_agent_parsing():
    from src.agents.core import GroundingFaithfulnessAuditor
    from unittest.mock import patch
    
    auditor = GroundingFaithfulnessAuditor()
    
    # 1. Valid APPROVED JSON parses correctly
    with patch.object(auditor, "_run_with_retry", return_value='{"status": "APPROVED", "blockers": []}'):
        res = auditor.audit_grounding("Content", "Course context", "Module context", "Topic context", {}, {})
        assert res["status"] == "APPROVED"
        assert res["blockers"] == []
        
    # 2. Valid FAILED JSON parses correctly
    failed_payload = '{"status": "FAILED", "blockers": [{"section": "Hook", "issue": "unsupported", "suggested_fix": "fix"}]}'
    with patch.object(auditor, "_run_with_retry", return_value=failed_payload):
        res = auditor.audit_grounding("Content", "Course context", "Module context", "Topic context", {}, {})
        assert res["status"] == "FAILED"
        assert len(res["blockers"]) == 1
        assert res["blockers"][0]["section"] == "Hook"
        
    # 3. Malformed auditor response is treated as failed
    with patch.object(auditor, "_run_with_retry", return_value="INVALID JSON PAYLOAD APPROVED"):
        res = auditor.audit_grounding("Content", "Course context", "Module context", "Topic context", {}, {})
        assert res["status"] == "FAILED"
        assert len(res["blockers"]) == 1
        assert "Malformed JSON" in res["blockers"][0]["issue"]


# =====================================================================
# Test Group 6: Orchestrator Pipeline & Repair Loops
# =====================================================================

def test_orchestrator_grounding_fail_routes_to_patch(tmp_path):
    from src.engine.orchestrator import Orchestrator
    from unittest.mock import MagicMock, patch
    
    course_input = {
        "course_title": "RAG Path Course",
        "course_context": "Test Path",
        "modules": [
            {
                "module_title": "Module One",
                "module_context": "M Context",
                "topics": [
                    {
                        "topic_title": "Topic One",
                        "concept": "T Concept"
                    }
                ]
            }
        ]
    }
    course = CourseStructure.model_validate(course_input)
    
    orch = Orchestrator(course=course, session_dir=tmp_path, run_type="new_run")
    
    # Mock generator to return a draft
    orch.generator.generate = MagicMock(return_value="""### Introduction
This is the intro.
### Core Concepts
Explanation.
### Practical Application
Code.
### Summary and Key Takeaways
- Bullet
""")
    
    # Mock Grounding Auditor to fail on first call, approve on second call
    orch.grounding_auditor.audit_grounding = MagicMock(side_effect=[
        {"status": "FAILED", "blockers": [{"section": "Core Concepts", "issue": "unsupported fact", "suggested_fix": "fix concept"}]},
        {"status": "APPROVED", "blockers": []}
    ])
    
    # Mock Semantic Evaluator to approve
    orch.semantic_evaluator.evaluate = MagicMock(return_value=MagicMock(issues=[]))
    
    # Mock Patch Editor to apply repair
    orch.patch_editor.edit_patch = MagicMock(return_value=MagicMock(
        operation="splice",
        replacement_markdown="### Core Concepts\nFixed explanation."
    ))
    
    with patch("src.validators.markdown_validator.validate_markdown_structure") as mock_struct, \
         patch("src.validators.lesson_contract_validator.validate_lesson_contract") as mock_contract:
         
        mock_struct.return_value = MagicMock(issues=[], detected_headings=["Core Concepts"])
        mock_contract.return_value = MagicMock(issues=[])
        
        status, final_draft = orch.run_submodule_pipeline(
            submodule=course.modules[0].topics[0],
            module_title="Module One",
            module_context="M Context"
        )
    
    # Ensure audit_grounding was called twice (due to loop retry after patch)
    assert orch.grounding_auditor.audit_grounding.call_count == 2
    # Ensure patch editor was called once with the grounding failure
    assert orch.patch_editor.edit_patch.call_count == 1
    call_args = orch.patch_editor.edit_patch.call_args[1]
    assert "Grounding Faithfulness Auditor found unsupported claims" in call_args["feedback"]
    assert call_args["heading"] == "Core Concepts"
    assert status == "approved"

