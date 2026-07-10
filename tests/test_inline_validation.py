import pytest
from backend.server import validate_patch_scope, validate_patch_grounding, run_patch_validation_loop

def test_scope_validation_preserves_headers():
    original = "#### Core Idea\nThe Enterprise AI Solution Architect acts as the bridge."
    
    # Valid: change text inside paragraph
    valid_patched = "#### Core Idea\nThe AI Architect acts as a primary bridge."
    assert validate_patch_scope(original, valid_patched) is True
    
    # Invalid: header stripped or modified
    invalid_patched_1 = "The Enterprise AI Solution Architect acts as the bridge."
    invalid_patched_2 = "#### Core Principle\nThe Enterprise AI Solution Architect acts as the bridge."
    assert validate_patch_scope(original, invalid_patched_1) is False
    assert validate_patch_scope(original, invalid_patched_2) is False

def test_scope_validation_only_modifies_selection():
    original = "1. **Defining AI Solution Ownership**: Ownership means taking responsibility.\n2. **Contrasting Roles**:\n* Developer vs. Architect"
    
    # Valid: modify only selected content
    valid_patched = "1. **Defining AI Solution Ownership**: Ownership means full responsibility.\n2. **Contrasting Roles**:\n* Developer vs. Architect"
    assert validate_patch_scope(original, valid_patched) is True

    # Invalid: edits text completely outside selection or trims sections
    invalid_patched = "1. **Defining AI Solution Ownership**: Ownership means taking responsibility."
    assert validate_patch_scope(original, invalid_patched) is False

def test_grounding_validation_maintains_terms():
    context = "Ensure they operate within the guardrails of identity and access management (ICAM) and data sovereignty."
    
    # Valid: retains ICAM and data sovereignty
    valid_patched = "Ensure developers operate within the guardrails of identity and access management (ICAM) and data sovereignty guidelines."
    assert validate_patch_grounding(valid_patched, context) is True
    
    # Invalid: removes key grounding term 'ICAM'
    invalid_patched = "Ensure they operate within the guardrails of identity control and data sovereignty."
    assert validate_patch_grounding(invalid_patched, context) is False

def test_validation_pipeline_retry_loop():
    # Mock generator that fails on first call, succeeds on second
    class MockEditor:
        def __init__(self):
            self.calls = 0
            self.input_tokens = 10
            self.output_tokens = 20
        def edit_patch(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return "Incorrect edit without ICAM"
            return "Ensure they operate within the guardrails of identity and access management (ICAM) and data sovereignty guidelines."
            
    mock_editor = MockEditor()
    context = "Ensure they operate within the guardrails of identity and access management (ICAM) and data sovereignty."
    original_text = "Ensure they operate within the guardrails of identity and access management (ICAM) and data sovereignty."
    
    final_patch = run_patch_validation_loop(
        editor=mock_editor,
        draft="draft",
        feedback="feedback",
        heading="heading",
        grounding_context=context,
        original_text=original_text
    )
    
    assert "ICAM" in final_patch
    assert mock_editor.calls == 2

def test_batch_validation_loop():
    from backend.server import run_batch_patch_validation
    
    class MockEditor:
        def __init__(self):
            self.calls = 0
            self.input_tokens = 5
            self.output_tokens = 5
        def edit_patch(self, draft, feedback, **kwargs):
            self.calls += 1
            # Mock behavior: if target draft has ICAM, but feedback is not addressed, return invalid.
            if "ICAM" in draft and self.calls == 1:
                return "Incorrect patch without acronym key"
            if "ICAM" in draft:
                return "Correct draft with ICAM preserved"
            return f"Updated {draft} based on {feedback}"
            
    mock_editor = MockEditor()
    edits = [
        {"original_text": "Ensure they operate within ICAM.", "instruction": "Make formal"},
        {"original_text": "Simple second paragraph.", "instruction": "Make concise"}
    ]
    
    results = run_batch_patch_validation(
        editor=mock_editor,
        edits=edits,
        grounding_context="Ensure they operate within ICAM. Simple second paragraph."
    )
    
    assert len(results) == 2
    assert "ICAM" in results[0]
    assert "Simple" in results[1]
    # The first edit had to retry once, so calls = 1 (edit 1 fail) + 1 (edit 1 success) + 1 (edit 2 success) = 3
    assert mock_editor.calls == 3

def test_html_to_markdown_sanitization():
    from backend.server import sanitize_html_to_markdown
    
    html_text = "Key challenges include:<ul><li><strong>Project Management</strong>: details.</li><li>Role Confusion</li></ul>"
    expected = "Key challenges include:\n* **Project Management**: details.\n* Role Confusion"
    
    sanitized = sanitize_html_to_markdown(html_text)
    assert "<ul>" not in sanitized
    assert "<li>" not in sanitized
    assert "<strong>" not in sanitized
    assert "**Project Management**" in sanitized
    assert "* Role Confusion" in sanitized
