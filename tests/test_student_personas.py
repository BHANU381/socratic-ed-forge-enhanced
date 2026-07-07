import pytest
from unittest.mock import MagicMock
from src.models.schemas import StudentPersona, CourseStructure
from src.engine.orchestrator import Orchestrator

def test_default_student_persona_generation(tmp_path):
    # Setup mock course structure with no student personas
    mock_course = MagicMock()
    mock_course.course_context = "Machine Learning Foundations"
    mock_course.student_personas = []
    mock_course.modules = []

    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=tmp_path,
        run_type="new_run"
    )

    # Invoke helper to format student personas
    personas_str = orchestrator._format_student_personas()

    # Assert that the default persona context was generated dynamically using course_context
    assert "Machine Learning Foundations" in personas_str
    assert "Target Name: Default Student" in personas_str


def test_student_personas_formatting_anonymity(tmp_path):
    # Setup mock course structure with custom student personas
    mock_course = MagicMock()
    mock_course.course_context = "Web Development"
    
    p1 = StudentPersona(name="Sarah the Sysadmin", context="IT operations and networking")
    p2 = StudentPersona(name="Alex the PM", context="Product management and user experience")
    mock_course.student_personas = [p1, p2]
    mock_course.modules = []

    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=tmp_path,
        run_type="new_run"
    )

    # Invoke helper to format student personas
    personas_str = orchestrator._format_student_personas()

    # Verify that the persona names are included in the formatted string for the LLM
    assert "Target Name: Sarah the Sysadmin" in personas_str
    assert "Target Name: Alex the PM" in personas_str
    assert "Target Name: Default Student" in personas_str

    # Verify that the contexts are in the formatted string
    assert "Target Context: IT operations and networking" in personas_str
    assert "Target Context: Product management and user experience" in personas_str
    assert "Target Context: A general learner seeking practical analogies related to: Web Development." in personas_str


def test_dynamic_word_count_scaling(tmp_path):
    mock_course = MagicMock()
    mock_course.course_context = "Python Basics"
    mock_course.prompt_theme = "otto2_structured"
    
    from src.models.schemas import LessonContract, SectionRequirement, HeadingRules, HeadingRuleMainContent
    heading_rules = HeadingRules(
        submodule_heading_level=2,
        main_content_heading=HeadingRuleMainContent(canonical="Hook", required_level=3, must_be_unique_per_submodule=True),
        required_child_section_level=4,
        optional_child_section_level=4,
        walkthrough_step_level=4
    )
    mock_course.lesson_contract = LessonContract(
        lesson_contract_name="test_contract",
        heading_rules=heading_rules,
        sections=[
            SectionRequirement(title="Persona Analogies", aliases=["Persona Analogies"], required=True, required_level=4, min_words=10, target_words=20)
        ]
    )
    
    p1 = StudentPersona(name="P1", context="Data science context")
    p2 = StudentPersona(name="P2", context="Finance context")
    mock_course.student_personas = [p1, p2]
    mock_course.modules = []

    orchestrator = Orchestrator(
        course=mock_course,
        session_dir=tmp_path,
        run_type="new_run"
    )
    
    # Run the dynamic scaling update
    # In orchestrator, we have 2 custom + 1 default = 3 total personas.
    orchestrator.adjust_contract_word_limits(num_personas=3)
    
    # Look up the "Persona Analogies" section in the active lesson contract
    persona_section = next(
        (sec for sec in orchestrator.lesson_contract.sections if sec.title == "Persona Analogies"),
        None
    )
    assert persona_section is not None
    assert persona_section.min_words == 600  # 200 * 3
    assert persona_section.target_words == 1050  # 350 * 3
