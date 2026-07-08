import pytest
from unittest.mock import MagicMock, patch
from src.engine.orchestrator import Orchestrator
from src.validators.lesson_contract_validator import validate_lesson_contract
from src.models.schemas import LessonContract, SectionRequirement, ValidationIssue
from src.agents.core import AnalogyAgent, AnalogyEvaluator

def test_analogy_agents_declaration():
    # Assert that both AnalogyAgent and AnalogyEvaluator can be instantiated
    generator = AnalogyAgent(theme="otto2_structured")
    evaluator = AnalogyEvaluator(theme="otto2_structured")
    assert generator is not None
    assert evaluator is not None

def test_placeholder_validation_bypass():
    # Setup contract with a Persona Analogies section requiring 800 words
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Core Idea", required_level=4, min_words=100),
            SectionRequirement(title="Persona Analogies", required_level=4, min_words=800)
        ]
    )
    
    # Text carrying a placeholder should bypass the min_words check for analogies
    draft_with_placeholder = (
        "#### Core Idea\nThis is a long core idea explaining technical concepts.\n\n"
        "#### Persona Analogies\n[PLACEHOLDER]"
    )
    
    res = validate_lesson_contract(draft_with_placeholder, contract)
    # Check that there are no blocker issues for Persona Analogies
    analogy_blockers = [i for i in res.issues if i.section == "Persona Analogies" and i.severity == "blocker"]
    assert len(analogy_blockers) == 0

def test_post_validation_analogy_pipeline_execution(tmp_path):
    # Setup mock course structure
    mock_course = MagicMock()
    mock_course.course_context = "Machine Learning Foundations"
    mock_course.student_personas = []
    mock_course.modules = []
    
    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=tmp_path,
        run_type="new_run"
    )
    
    # Assert that the new agents are initialized on the orchestrator
    assert hasattr(orchestrator, "analogy_generator")
    assert hasattr(orchestrator, "analogy_evaluator")

def test_pipeline_replacing_placeholder_on_success(tmp_path):
    from src.models.schemas import CourseStructure, Topic
    course_payload = {
        "course_title": "AWS Cloud",
        "course_context": "AWS Cloud",
        "prompt_theme": "otto2_structured",
        "modules": []
    }
    course = CourseStructure(**course_payload)
    orchestrator = Orchestrator(course=course, session_dir=tmp_path, run_type="new_run")
    
    # Mock generator and approved evaluator
    orchestrator.analogy_generator.generate = MagicMock(return_value="##### Default Student\nApproved analogies content.")
    orchestrator.analogy_evaluator.evaluate = MagicMock(return_value={"status": "APPROVED", "reasons": []})

    # Call run_submodule_pipeline on a mock core approved draft
    draft_core = "#### Persona Analogies\n[PLACEHOLDER]"
    submodule = Topic(
        topic_title="Cloud",
        concept="Cloud computing",
        breakdown="Breakdown context",
        edge_cases="Legacy systems",
        common_mistakes=["Mistake 1"],
        action_items=["Item 1"]
    )
    
    # Mocking validator and other agents to bypass main loops
    with patch("src.validators.markdown_validator.validate_markdown_structure", return_value=MagicMock(issues=[])), \
         patch("src.validators.lesson_contract_validator.validate_lesson_contract", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.generator, "generate", return_value=draft_core), \
         patch.object(orchestrator.semantic_evaluator, "evaluate", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.grounding_auditor, "audit_grounding", return_value={"status": "APPROVED"}):
         
         status, compiled_result = orchestrator.run_submodule_pipeline(
             submodule=submodule,
             module_title="Module 1",
             module_context="Some module context text."
         )
         
         assert status == "approved"
         # Check that the placeholder is replaced with the analogies text
         assert "[PLACEHOLDER]" not in compiled_result
         assert "Approved analogies content." in compiled_result

def test_pipeline_triggering_repair_and_fallback(tmp_path):
    from src.models.schemas import CourseStructure, Topic
    course_payload = {
        "course_title": "AWS Cloud",
        "course_context": "AWS Cloud",
        "prompt_theme": "otto2_structured",
        "modules": []
    }
    course = CourseStructure(**course_payload)
    orchestrator = Orchestrator(course=course, session_dir=tmp_path, run_type="new_run")

    # Mock generator returning rejected content, evaluator returning REJECTED
    orchestrator.analogy_generator.generate = MagicMock(return_value="##### Default Student\nBad analogies content.")
    orchestrator.analogy_evaluator.evaluate = MagicMock(return_value={"status": "REJECTED", "reasons": ["name leak"]})

    draft_core = "#### Persona Analogies\n[PLACEHOLDER]"
    submodule = Topic(
        topic_title="Cloud",
        concept="Cloud computing",
        breakdown="Breakdown context",
        edge_cases="Legacy systems",
        common_mistakes=["Mistake 1"],
        action_items=["Item 1"]
    )

    with patch("src.validators.markdown_validator.validate_markdown_structure", return_value=MagicMock(issues=[])), \
         patch("src.validators.lesson_contract_validator.validate_lesson_contract", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.generator, "generate", return_value=draft_core), \
         patch.object(orchestrator.semantic_evaluator, "evaluate", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.grounding_auditor, "audit_grounding", return_value={"status": "APPROVED"}):

         status, compiled_result = orchestrator.run_submodule_pipeline(
             submodule=submodule,
             module_title="Module 1",
             module_context="Some module context text."
         )

         # Double failure triggers fallback
         assert status == "approved"
         assert "[PLACEHOLDER]" not in compiled_result
         # Verify the last generated custom analogy text is preserved
         assert "Bad analogies content." in compiled_result

def test_telemetry_keys_exist(tmp_path):
    mock_course = MagicMock()
    mock_course.course_context = "AWS Cloud"
    mock_course.student_personas = []
    mock_course.modules = []

    orchestrator = Orchestrator(course=mock_course, session_dir=tmp_path, run_type="new_run")
    assert "analogy_generator_attempts" in orchestrator.telemetry
    assert "analogy_evaluator_status" in orchestrator.telemetry
    assert "analogy_evaluator_blockers" in orchestrator.telemetry
    assert "analogy_fallback_triggered" in orchestrator.telemetry

def test_telemetry_updated_on_success(tmp_path):
    from src.models.schemas import CourseStructure, Topic
    course_payload = {
        "course_title": "AWS Cloud",
        "course_context": "AWS Cloud",
        "prompt_theme": "otto2_structured",
        "modules": []
    }
    course = CourseStructure(**course_payload)
    orchestrator = Orchestrator(course=course, session_dir=tmp_path, run_type="new_run")
    
    orchestrator.analogy_generator.generate = MagicMock(return_value="##### Default Student\nApproved analogies content.")
    orchestrator.analogy_evaluator.evaluate = MagicMock(return_value={"status": "APPROVED", "reasons": []})

    draft_core = "#### Persona Analogies\n[PLACEHOLDER]"
    submodule = Topic(
        topic_title="Cloud",
        concept="Cloud computing",
        breakdown="Breakdown context",
        edge_cases="Legacy systems",
        common_mistakes=["Mistake 1"],
        action_items=["Item 1"]
    )
    
    with patch("src.validators.markdown_validator.validate_markdown_structure", return_value=MagicMock(issues=[])), \
         patch("src.validators.lesson_contract_validator.validate_lesson_contract", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.generator, "generate", return_value=draft_core), \
         patch.object(orchestrator.semantic_evaluator, "evaluate", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.grounding_auditor, "audit_grounding", return_value={"status": "APPROVED"}):
         
         status, compiled_result = orchestrator.run_submodule_pipeline(
             submodule=submodule,
             module_title="Module 1",
             module_context="Some module context text."
         )
         
         assert orchestrator.telemetry["analogy_generator_attempts"] == 1
         assert orchestrator.telemetry["analogy_evaluator_status"] == "passed"
         assert orchestrator.telemetry["analogy_fallback_triggered"] is False
         assert orchestrator.telemetry["submodule_telemetry"]["Module 1"]["Cloud"]["analogy"] == "1"

def test_telemetry_updated_on_fallback(tmp_path):
    from src.models.schemas import CourseStructure, Topic
    course_payload = {
        "course_title": "AWS Cloud",
        "course_context": "AWS Cloud",
        "prompt_theme": "otto2_structured",
        "modules": []
    }
    course = CourseStructure(**course_payload)
    orchestrator = Orchestrator(course=course, session_dir=tmp_path, run_type="new_run")
    
    orchestrator.analogy_generator.generate = MagicMock(return_value="##### Default Student\nBad analogies content.")
    orchestrator.analogy_evaluator.evaluate = MagicMock(return_value={"status": "REJECTED", "reasons": ["name leak"]})

    draft_core = "#### Persona Analogies\n[PLACEHOLDER]"
    submodule = Topic(
        topic_title="Cloud",
        concept="Cloud computing",
        breakdown="Breakdown context",
        edge_cases="Legacy systems",
        common_mistakes=["Mistake 1"],
        action_items=["Item 1"]
    )
    
    with patch("src.validators.markdown_validator.validate_markdown_structure", return_value=MagicMock(issues=[])), \
         patch("src.validators.lesson_contract_validator.validate_lesson_contract", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.generator, "generate", return_value=draft_core), \
         patch.object(orchestrator.semantic_evaluator, "evaluate", return_value=MagicMock(issues=[])), \
         patch.object(orchestrator.grounding_auditor, "audit_grounding", return_value={"status": "APPROVED"}):
         
         status, compiled_result = orchestrator.run_submodule_pipeline(
             submodule=submodule,
             module_title="Module 1",
             module_context="Some module context text."
         )
         
         assert orchestrator.telemetry["analogy_generator_attempts"] == 2
         assert orchestrator.telemetry["analogy_evaluator_status"] == "failed"
         assert orchestrator.telemetry["analogy_fallback_triggered"] is True
         assert orchestrator.telemetry["submodule_telemetry"]["Module 1"]["Cloud"]["analogy"] == "F"


