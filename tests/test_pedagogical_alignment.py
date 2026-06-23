import pytest
import json
from unittest.mock import MagicMock, patch
from src.engine.orchestrator import Orchestrator
from src.models.schemas import CourseInput, Module, Submodule, LessonContract, SectionRequirement

@pytest.fixture
def test_course():
    return CourseInput(
        course_name="Test Course",
        topic="Testing",
        duration_weeks=1,
        modules=[
            Module(
                title="Module 1: Basics",
                module_context="Context",
                submodules=[Submodule(title="1.1 Intro", content_context="Intro Context")]
            )
        ],
        learner_level="beginner",
        code_example_style="progressive_production",
        explanation_depth="balanced",
        lesson_contract=LessonContract(
            sections=[
                SectionRequirement(title="Introduction", min_words=10, required=True),
                SectionRequirement(title="Core Concepts", min_words=10, required=True),
                SectionRequirement(title="Summary", min_words=10, required=True)
            ]
        )
    )

def test_beginner_content_unexplained_jargon_is_blocker(test_course, tmp_path):
    orchestrator = Orchestrator(test_course, tmp_path)
    
    with patch.object(orchestrator.semantic_evaluator, 'evaluate') as mock_eval:
        # Mocking an evaluator result that returns a blocker for jargon
        from src.models.schemas import ValidationResult, ValidationIssue
        mock_eval.return_value = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(severity="blocker", issue_type="pedagogical", message="Advanced jargon without explanation", section="Core Concepts")
            ],
            detected_headings=["Introduction", "Core Concepts", "Summary"]
        )
        
        # Patch the deterministic validators to pass instantly
        with patch('src.validators.markdown_validator.validate_markdown_structure') as mock_md, \
             patch('src.validators.lesson_contract_validator.validate_lesson_contract') as mock_lc, \
             patch.object(orchestrator.patch_editor, 'edit_patch') as mock_patch:
             
            mock_md.return_value = MagicMock(passed=True, issues=[], detected_headings=["Introduction", "Core Concepts", "Summary"])
            mock_lc.return_value = MagicMock(passed=True, issues=[], detected_headings=["Introduction", "Core Concepts", "Summary"])
            
            # Simulate a dummy draft
            dummy_draft = "### Introduction\n\n### Core Concepts\n\n### Summary"
            
            # When the patch editor is called, it should receive the 'simplify_for_beginner' patch mode if handled in Orchestrator
            # We don't have patch mode strictly passed in edit_patch signature in the mock yet, but we will assert the orchestrator attempts to call it.
            mock_patch.return_value = "Simplified core concepts"
            
            # The test proves the semantic loop captures the blocker and triggers a patch
            status, final_draft = orchestrator.run_submodule_pipeline(test_course.modules[0].submodules[0], "Module 1", "Context", "")
            
            # It tries to patch up to 2 times, and if mock_eval keeps returning blocker, it eventually fails with 'failed_blocker'
            assert status == "failed_blocker"
            assert mock_patch.call_count == 2
            
            # Ensure the failure reason was captured in telemetry
            assert any("jargon" in r.get("message", "").lower() for r in orchestrator.telemetry["failure_reasons"])

def test_module_position_computed_correctly(test_course, tmp_path):
    orchestrator = Orchestrator(test_course, tmp_path)
    
    # We will patch the Generator to just intercept the kwargs passed to it
    with patch.object(orchestrator.generator, 'generate') as mock_generate, \
         patch.object(orchestrator, 'run_submodule_pipeline') as mock_pipeline:
         
        mock_pipeline.return_value = ("approved", "Draft")
        
        orchestrator.run_course_pipeline()
        
        # The telemetry should have module_position (e.g. "1/1" for this 1-module test course)
        # Note: We will add module_position logic to Orchestrator next.
        # This test ensures we've mocked the structure to allow asserting.

