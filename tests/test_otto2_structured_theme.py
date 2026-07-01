import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.engine.orchestrator import Orchestrator
from src.models.schemas import CourseInput, Module, Submodule, ValidationResult, ValidationIssue
from src.validators.lesson_contract_validator import validate_lesson_contract
from src.validators.markdown_validator import validate_markdown_structure

def test_theme_discovery_and_selection(tmp_path):
    # Verify the theme directories exist
    prompts_dir = Path("src/prompts")
    assert (prompts_dir / "otto2").is_dir()
    assert (prompts_dir / "otto2_structured").is_dir()
    
    # Verify we can load the contract file
    contract_file = prompts_dir / "otto2_structured" / "contract.json"
    assert contract_file.exists()
    
    with open(contract_file, "r") as f:
        contract_data = json.load(f)
    
    # Assert contract structure requirements
    headings = [s["title"] for s in contract_data.get("sections", [])]
    assert "Hook" in headings
    assert "Core Idea" in headings
    assert "Lesson Breakdown" in headings
    assert "Practical Walkthrough" in headings
    assert "Edge Cases" in headings
    assert "Common Mistakes" in headings
    assert "Action Items" in headings
    assert "Why It Matters" in headings
    
    # Assert hidden fields are NOT in headings
    assert "Constraints" not in headings
    assert "Evaluation Path" not in headings
    assert "Expert Heuristic" not in headings
    assert "Module Constraints" not in headings

def test_contract_validation_success():
    # Construct a valid markdown matching the new schema
    valid_markdown = """## Submodule: 1.1 Test Submodule

### Hook: A short hook line here.

#### Core Idea
This is the core concept of the topic. It should explain what we are doing.

#### Lesson Breakdown
This section lists the conceptual details of the lesson content.

#### Practical Walkthrough
This section contains a step-by-step example.

#### Edge Cases
What could go wrong and how to handle it.

#### Common Mistakes
Common traps when implementing this.

#### Action Items
Steps the learner should execute.

#### Why It Matters
Connecting this to our overall engineering goals.
"""
    # Load contract details
    contract_file = Path("src/prompts/otto2_structured/contract.json")
    if not contract_file.exists():
        pytest.fail("contract.json not found for otto2_structured")
        
    with open(contract_file, "r") as f:
        contract_data = json.load(f)
        
    from src.models.schemas import LessonContract
    contract = LessonContract(**contract_data)
    
    res = validate_lesson_contract(valid_markdown, contract)
    assert not [i for i in res.issues if i.severity == "blocker"]

def test_contract_validation_fails_on_missing_sections():
    # Missing Action Items and Edge Cases
    invalid_markdown = """## Submodule: 1.1 Test Submodule

### Hook: A short hook line here.

#### Core Idea
Core idea text.

#### Lesson Breakdown
Lesson breakdown text.

#### Practical Walkthrough
Practical walkthrough text.

#### Common Mistakes
Common mistakes text.

#### Why It Matters
Why it matters text.
"""
    contract_file = Path("src/prompts/otto2_structured/contract.json")
    if not contract_file.exists():
        pytest.fail("contract.json not found for otto2_structured")
        
    with open(contract_file, "r") as f:
        contract_data = json.load(f)
        
    from src.models.schemas import LessonContract
    contract = LessonContract(**contract_data)
    
    res = validate_lesson_contract(invalid_markdown, contract)
    blockers = [i for i in res.issues if i.severity == "blocker"]
    assert len(blockers) > 0

def test_backward_compatibility_otto2_vs_structured():
    # Load stable otto2 contract
    otto2_contract_file = Path("src/prompts/otto2/contract.json")
    with open(otto2_contract_file, "r") as f:
        otto2_data = json.load(f)
    otto2_headings = [s["title"] for s in otto2_data.get("sections", [])]
    
    # Load new otto2_structured contract
    structured_contract_file = Path("src/prompts/otto2_structured/contract.json")
    with open(structured_contract_file, "r") as f:
        structured_data = json.load(f)
    structured_headings = [s["title"] for s in structured_data.get("sections", [])]
    
    # Assert old behaves as original compact and new behaves as expanded structured
    assert "Implementation" in otto2_headings
    assert "Practical Walkthrough" not in otto2_headings
    
    assert "Practical Walkthrough" in structured_headings
    assert "Lesson Breakdown" in structured_headings
    assert "Edge Cases" in structured_headings
    assert "Common Mistakes" in structured_headings
    assert "Action Items" in structured_headings
    assert "Implementation" not in structured_headings

def test_generator_prompt_snapshot():
    generator_file = Path("src/prompts/otto2_structured/content_generator.md")
    assert generator_file.exists()
    content = generator_file.read_text(encoding="utf-8")
    
    # Check internal guidance fields text
    assert "constraints" in content
    assert "evaluation_path" in content
    assert "expert_heuristic" in content
    assert "module_constraints" in content
    assert "internal guidance fields" in content
    assert "Do NOT generate visible headings called:" in content
    
    # Check tool stack rules
    assert "tool_stack" in content
    assert "Do not create a separate tools section" in content
    
    # Check grounding rules
    assert "Use the course JSON as the teaching target" in content
    assert "Use grounding_context as supporting source material" in content
    
    # Check placeholders rules
    assert "Never leave authoring placeholders such as [TODO]" in content
    assert "[EXPECTED BEHAVIOR]" in content

def test_semantic_evaluator_snapshot():
    evaluator_file = Path("src/prompts/otto2_structured/semantic_evaluator.md")
    assert evaluator_file.exists()
    content = evaluator_file.read_text(encoding="utf-8")
    
    # Check visible sections and internal guidance rules
    assert "#### Lesson Breakdown" in content
    assert "#### Practical Walkthrough" in content
    assert "Do not require visible headings for constraints" in content
    assert "Do NOT require old hardcoded 600-word sections" in content

def test_patch_editor_snapshot():
    patch_file = Path("src/prompts/otto2_structured/patch_editor.md")
    assert patch_file.exists()
    content = patch_file.read_text(encoding="utf-8")
    
    # Check sections known
    assert "#### Lesson Breakdown" in content
    assert "#### Practical Walkthrough" in content
    assert "Do NOT create headings for constraints" in content

