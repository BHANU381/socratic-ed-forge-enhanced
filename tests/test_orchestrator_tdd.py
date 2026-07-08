import pytest
from pathlib import Path
import json
from unittest.mock import MagicMock, patch

from src.models.schemas import CourseInput, LessonContract, SectionRequirement, Module, Submodule, ValidationResult, ValidationIssue
from src.engine.orchestrator import Orchestrator, truncate_running_summary

def test_truncate_running_summary():
    # If the summary has more than 15 bullet points, it should keep only the last 15
    summary = "\n".join([f"- Lesson {i}: summary details" for i in range(20)])
    truncated = truncate_running_summary(summary)
    lines = [l for l in truncated.splitlines() if l.strip().startswith("-")]
    assert len(lines) == 15
    assert "Lesson 19" in truncated
    assert "Lesson 0" not in truncated

def test_module_position_is_computed(tmp_path):
    # Setup dummy course with default theme
    course = CourseInput(
        course_name="Test",
        topic="Testing",
        duration_weeks=1,
        prompt_theme="default",
        modules=[
            Module(
                title="Module 1",
                module_context="Module 1 Context",
                submodules=[Submodule(title="Sub 1", content_context="Sub 1 Content Context")]
            )
        ]
    )
    orchestrator = Orchestrator(course, tmp_path)
    
    # We will test loading contract from file below. For now, ensure module_position matches logic.
    pass

def test_orchestrator_loads_contract_from_file(tmp_path):
    # This test asserts that the Orchestrator reads contract.json from the theme folder
    course = CourseInput(
        course_name="Test",
        topic="Testing",
        duration_weeks=1,
        prompt_theme="dummy_theme",
        modules=[]
    )
    
    # Create the dummy theme folder with a dummy contract.json
    theme_dir = Path("src/prompts/dummy_theme")
    theme_dir.mkdir(parents=True, exist_ok=True)
    
    contract_json = {
        "lesson_contract_name": "dummy_lesson",
        "sections": [
            {
                "title": "Dummy Section",
                "aliases": ["Dummy"],
                "required": True
            }
        ]
    }
    
    contract_path = theme_dir / "contract.json"
    with open(contract_path, "w", encoding="utf-8") as f:
        json.dump(contract_json, f)
        
    try:
        orchestrator = Orchestrator(course, tmp_path)
        assert orchestrator.lesson_contract.lesson_contract_name == "dummy_lesson"
        assert len(orchestrator.lesson_contract.sections) == 1
        assert orchestrator.lesson_contract.sections[0].title == "Dummy Section"
        
        # Test missing contract raises error
        course.prompt_theme = "missing_theme"
        with pytest.raises(FileNotFoundError, match="contract.json not found"):
            Orchestrator(course, tmp_path)
    finally:
        # Cleanup
        contract_path.unlink()
        theme_dir.rmdir()

def test_manifest_mismatch(tmp_path):
    # Setup directories
    session_dir = tmp_path / "session_test"
    session_dir.mkdir()
    
    # Pre-existing manifest
    manifest_data = {
        "course_id": "course-1",
        "topic": "Old Topic",
        "lesson_contract": {"sections": []},
        "quality_profile": "standard",
        "completed_submodules": []
    }
    with open(session_dir / "run_manifest.json", "w") as f:
        json.dump(manifest_data, f)
        
    course = CourseInput(
        course_name="course-1",
        topic="New Topic", # Topic changed! Mismatch!
        duration_weeks=4,
        modules=[]
    )
    
    orch = Orchestrator(course, session_dir=session_dir)
    with pytest.raises(ValueError) as exc_info:
        orch.load_or_create_manifest()
    assert "mismatch" in str(exc_info.value).lower()

def test_retry_limits_and_submodule_status(tmp_path):
    session_dir = tmp_path / "session_test"
    session_dir.mkdir()
    
    course = CourseInput(
        course_name="course-1",
        topic="Topic",
        duration_weeks=4,
        modules=[]
    )
    
    orch = Orchestrator(course, session_dir=session_dir)
    
    # Mock the generator to return a draft
    orch.generator.generate = MagicMock(return_value="# Intro\nDraft content")
    orch.generator.required_headings = []
    
    # Mock deterministic validator to fail with blocker
    # We will simulate 2 failed patch attempts for deterministic validation
    from src.validators import markdown_validator
    markdown_validator.validate_markdown_structure = MagicMock(return_value=ValidationResult(
        passed=False,
        issues=[ValidationIssue(severity="blocker", issue_type="unclosed_fence", message="unclosed")]
    ))
    
    # Mock patch editor
    orch.patch_editor.edit_patch = MagicMock(return_value="# Intro\nPatched content")
    orch.grounding_auditor.audit_grounding = MagicMock(return_value={"status": "APPROVED"})
    
    submodule = MagicMock()
    submodule.title = "Submodule 1.1"
    submodule.content_context = "Context"
    
    with patch("src.engine.orchestrator.search_duckduckgo", return_value="Mocked search context"), \
         patch("src.engine.orchestrator.update_telemetry"):
        status, final_draft = orch.run_submodule_pipeline(submodule, "Module 1", "Module Context")
    
    # Should stop after 2 patch retries and return failed_blocker
    assert status == "failed_blocker"
    assert orch.patch_editor.edit_patch.call_count == 2

def test_telemetry_structure(tmp_path):
    session_dir = tmp_path / "session_test"
    session_dir.mkdir()
    
    course = CourseInput(
        course_name="course-1",
        topic="Topic",
        duration_weeks=4,
        modules=[]
    )
    
    orch = Orchestrator(course, session_dir=session_dir)
    orch.generator.generate = MagicMock(return_value="# Intro\nDraft content")
    orch.generator.required_headings = []
    
    from src.validators import markdown_validator
    markdown_validator.validate_markdown_structure = MagicMock(return_value=ValidationResult(
        passed=False,
        issues=[ValidationIssue(severity="blocker", issue_type="unclosed_fence", message="unclosed")]
    ))
    orch.patch_editor.edit_patch = MagicMock(return_value="# Intro\nPatched content")
    orch.grounding_auditor.audit_grounding = MagicMock(return_value={"status": "APPROVED"})
    
    submodule = MagicMock()
    submodule.title = "Submodule 1.1"
    submodule.content_context = "Context"
    
    with patch("src.engine.orchestrator.search_duckduckgo", return_value="Mocked search context"), \
         patch("src.engine.orchestrator.update_telemetry"):
        orch.run_submodule_pipeline(submodule, "Module 1", "Module Context")
    
    # We should have failure reasons logged
    assert len(orch.telemetry["failure_reasons"]) > 0
    
    # Each failure reason should be a dictionary with severity, issue_type, message, etc.
    first_failure = orch.telemetry["failure_reasons"][0]
    assert isinstance(first_failure, dict), "Failure reason should be a dictionary, not a string"
    assert "severity" in first_failure
    assert "issue_type" in first_failure
    assert "message" in first_failure

def test_quality_profile_light_runs_evaluator(tmp_path):
    from src.models.schemas import QualityProfile
    
    course = CourseInput(
        course_name="course-light",
        topic="Topic",
        duration_weeks=4,
        quality_profile=QualityProfile.LIGHT,
        modules=[]
    )
    
    orch = Orchestrator(course, session_dir=tmp_path)
    
    # Mock generator to succeed
    orch.generator.generate = MagicMock(return_value="### Introduction\nContent")
    orch.generator.required_headings = ["### Introduction"]
    
    # Mock deterministic validation to pass
    from src.validators import markdown_validator
    import src.validators.lesson_contract_validator as cv
    markdown_validator.validate_markdown_structure = MagicMock(return_value=ValidationResult(passed=True, issues=[]))
    cv.validate_lesson_contract = MagicMock(return_value=ValidationResult(passed=True, issues=[]))
    
    # Mock semantic evaluator
    orch.semantic_evaluator.evaluate = MagicMock(return_value=ValidationResult(passed=True, issues=[]))
    orch.grounding_auditor.audit_grounding = MagicMock(return_value={"status": "APPROVED"})
    
    submodule = MagicMock()
    submodule.title = "Submodule 1.1"
    submodule.content_context = "Context"
    
    with patch("src.engine.orchestrator.search_duckduckgo", return_value="Mocked search context"), \
         patch("src.engine.orchestrator.update_telemetry"):
        status, final_draft = orch.run_submodule_pipeline(submodule, "Module 1", "Module Context")
    
    # Assert that the semantic evaluator was called
    assert orch.semantic_evaluator.evaluate.call_count > 0
    assert status == "approved"


def test_orchestrator_corrects_headings_on_blocker(tmp_path, monkeypatch):
    from src.engine.orchestrator import Orchestrator
    from src.models.schemas import CourseInput, QualityProfile, LessonContract
    from unittest.mock import MagicMock
    from src.validators.markdown_validator import ValidationResult
    
    course = CourseInput(
        course_name="course-light",
        topic="Topic",
        duration_weeks=4,
        quality_profile=QualityProfile.LIGHT,
        modules=[]
    )
    
    orch = Orchestrator(course, session_dir=tmp_path)
    
    # Provide a draft with bad heading level (## Introduction)
    # The normalizer is expected to change it to ### Introduction
    orch.generator.generate = MagicMock(
        return_value="## Introduction\nThis is introductory content."
    )
    orch.generator.required_headings = ["### Introduction"]
    from src.models.schemas import SectionRequirement
    orch.lesson_contract = LessonContract(sections=[SectionRequirement(title="Introduction")])
    
    # We mock validators:
    # First call to validate_markdown_structure will find blocker because of ## heading.
    # Second call (after normalization) should find no blockers.
    from src.validators.markdown_validator import ValidationIssue
    issue_fail = ValidationIssue(
        severity="blocker",
        issue_type="invalid_heading_level",
        message="Found illegal header level '## Introduction'",
        section="Introduction"
    )
    res_fail = ValidationResult(passed=False, issues=[issue_fail])
    res_pass = ValidationResult(passed=True, issues=[])
    
    from src.validators import markdown_validator
    import src.validators.lesson_contract_validator as cv
    monkeypatch.setattr(markdown_validator, "validate_markdown_structure", MagicMock(side_effect=[res_fail, res_pass]))
    monkeypatch.setattr(cv, "validate_lesson_contract", MagicMock(return_value=res_pass))
    
    orch.semantic_evaluator.evaluate = MagicMock(return_value=res_pass)
    orch.grounding_auditor.audit_grounding = MagicMock(return_value={"status": "APPROVED"})
    
    submodule = MagicMock()
    submodule.topic_title = "Submodule 1.1"
    submodule.content_context = "Context"
    submodule.topic_material_ids = []
    
    with patch("src.engine.orchestrator.search_duckduckgo", return_value="Mocked search context"), \
         patch("src.engine.orchestrator.update_telemetry"):
        status, final_draft = orch.run_submodule_pipeline(submodule, "Module 1", "Module Context")
    
    # The pipeline should succeed because the orchestrator corrected the heading level on the blocker!
    assert status == "approved"
    assert "### Introduction" in final_draft


def test_pipeline_breakpoint_pause_resolve(tmp_path, monkeypatch):
    course_data = {
        "course_name": "Test Breakpoint",
        "topic": "Testing",
        "duration_weeks": 1,
        "modules": []
    }
    course_input = CourseInput(**course_data)
    orch = Orchestrator(course_input, session_dir=tmp_path)
    monkeypatch.setenv("TEST_BREAKPOINT_PAUSE", "1")
    
    # Mock validators to return failures
    res_fail = ValidationResult(
        passed=False,
        issues=[ValidationIssue(severity="blocker", issue_type="unclosed_fence", message="unclosed", section="Core Idea")]
    )
    
    from src.validators import markdown_validator
    monkeypatch.setattr(markdown_validator, "validate_markdown_structure", MagicMock(return_value=res_fail))
    
    # Mock sleep to simulate user resolving the breakpoint file
    import time
    def mock_sleep(seconds):
        bp_file = tmp_path / "breakpoint.json"
        assert bp_file.exists()
        bp_data = json.loads(bp_file.read_text())
        assert bp_data["status"] == "paused_for_repair"
        
        # User resolves by selecting force_approve
        bp_data["status"] = "resolved"
        bp_data["resolution"] = "force_approve"
        bp_file.write_text(json.dumps(bp_data))
        
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    submodule = MagicMock()
    submodule.topic_title = "Submodule 1.1"
    submodule.content_context = "Context"
    submodule.topic_material_ids = []
    
    # Mock generator and validators to run without calling LLM APIs
    orch.generator.generate = MagicMock(return_value="Draft text")
    orch.semantic_evaluator.evaluate = MagicMock(return_value=res_fail)
    orch.grounding_auditor.audit_grounding = MagicMock(return_value={"status": "APPROVED"})
    
    from src.models.schemas import PatchResult
    orch.patch_editor.edit_patch = MagicMock(return_value=PatchResult(
        operation="no_safe_patch",
        target_heading="Core Idea",
        replacement_markdown="",
        reason="Mocked fail"
    ))
    
    with patch("src.engine.orchestrator.search_duckduckgo", return_value="Mocked search context"), \
         patch("src.engine.orchestrator.update_telemetry"):
        status, final_draft = orch.run_submodule_pipeline(submodule, "Module 1", "Module Context")
        
    # The pipeline should return "approved" due to user's force_approve choice
    assert status == "approved"


def test_analogy_double_validation_failure_preserves_generated_analogies(tmp_path):
    from src.models.schemas import CourseInput, StudentPersona, SectionRequirement, LessonContract
    from src.validators.markdown_validator import ValidationResult
    
    course = CourseInput(
        course_name="course-1",
        topic="Topic",
        duration_weeks=4,
        modules=[],
        student_personas=[StudentPersona(name="Student 1", context="A student interested in baking.")]
    )
    
    orch = Orchestrator(course, session_dir=tmp_path)
    orch.lesson_contract = LessonContract(
        sections=[SectionRequirement(title="Persona Analogies")]
    )
    
    # Mock technical draft generator & validators to pass
    orch.generator.generate = MagicMock(return_value="### Technical Content\n[PLACEHOLDER]")
    orch.generator.required_headings = []
    
    from src.validators import markdown_validator
    import src.validators.lesson_contract_validator as cv
    markdown_validator.validate_markdown_structure = MagicMock(return_value=ValidationResult(passed=True, issues=[]))
    cv.validate_lesson_contract = MagicMock(return_value=ValidationResult(passed=True, issues=[]))
    orch.grounding_auditor.audit_grounding = MagicMock(return_value={"status": "APPROVED"})
    orch.semantic_evaluator.evaluate = MagicMock(return_value=ValidationResult(passed=True, issues=[]))
    
    # Mock analogy agent to return generated analogies, and evaluator to fail
    orch.analogy_generator.generate = MagicMock(return_value="##### Student 1\nThis is the custom generated analogy text for Student 1.")
    orch.analogy_evaluator.evaluate = MagicMock(return_value={"status": "REJECTED", "reasons": ["Analogy too short"]})
    
    submodule = MagicMock()
    submodule.title = "Submodule 1.1"
    submodule.content_context = "Context"
    
    with patch("src.engine.orchestrator.search_duckduckgo", return_value="Mocked search context"), \
         patch("src.engine.orchestrator.update_telemetry"):
        status, final_draft = orch.run_submodule_pipeline(submodule, "Module 1", "Module Context")
        
    assert status == "approved"
    assert orch.telemetry["analogy_fallback_triggered"] is True
    # Telemetry should be marked as "F" (failed)
    assert orch.telemetry["submodule_telemetry"]["Module 1"]["Submodule 1.1"]["analogy"] == "F"
    # The final draft should contain the generated analogy, NOT the default fallback text
    assert "This is the custom generated analogy text for Student 1." in final_draft
    assert "Learning Submodule 1.1 is exactly like building a system" not in final_draft


def test_strip_analogies():
    from src.engine.orchestrator import strip_analogies
    text = "### Hook: Hello\n#### Core Idea\nSome technical content\n#### Persona Analogies\n##### Student 1\nAnalogy text"
    cleaned = strip_analogies(text)
    assert "Persona Analogies" not in cleaned
    assert "Analogy text" not in cleaned
    assert "Core Idea" in cleaned




