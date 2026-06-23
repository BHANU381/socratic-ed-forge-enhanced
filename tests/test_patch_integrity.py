import pytest
from src.utils.patch_utils import apply_section_patch
from src.models.schemas import PatchResult

def test_patch_result_schema():
    # Verify the schema parses correctly
    data = {
        "operation": "replace_section",
        "target_heading": "### Practical Application",
        "replacement_markdown": "### Practical Application\n\nThis is the new content.",
        "reason": "Fixing jargon"
    }
    patch = PatchResult(**data)
    assert patch.operation == "replace_section"
    assert patch.target_heading == "### Practical Application"

def test_apply_section_patch_exact_replacement():
    draft = """## Submodule: 1.1 Intro
    
### Introduction
Intro content here.

### Practical Application
Old application content.
Needs replacing.

### Summary
Summary content.
"""
    patch_content = "### Practical Application\n\nNew application content.\nAll fresh!"
    
    result = apply_section_patch(draft, "### Practical Application", patch_content)
    
    assert "New application content." in result
    assert "All fresh!" in result
    assert "Old application content." not in result
    assert "### Introduction" in result
    assert "### Summary" in result

def test_apply_section_patch_child_headings():
    draft = """### Core Concepts
Some concepts.
#### Concept 1
More detail.
#### Concept 2
Even more.

### Practical Application
Do the thing.
"""
    patch_content = "### Core Concepts\n\nNew concepts.\n#### Concept A\nDetails."
    
    result = apply_section_patch(draft, "### Core Concepts", patch_content)
    
    assert "New concepts." in result
    assert "#### Concept A" in result
    assert "Concept 1" not in result
    assert "Concept 2" not in result
    assert "### Practical Application" in result

def test_apply_section_patch_removes_duplicate_heading_in_patch():
    draft = """### Summary\n\nOld text."""
    # Sometimes LLMs output the heading inside the replacement content when they shouldn't, 
    # or the prompt expects them to. The logic should ensure we don't end up with:
    # ### Summary
    # ### Summary
    patch_content = "### Summary\n\nNew text."
    
    result = apply_section_patch(draft, "### Summary", patch_content)
    
    # Check that '### Summary' only appears once in the patched section
    assert result.count("### Summary") == 1
    assert "New text" in result

from src.validators.markdown_validator import detect_duplicate_content

def test_markdown_validator_duplicate_content():
    content = """### Intro

This is a somewhat long paragraph that is going to be duplicated later in the file.
We need to make sure the hashing logic catches it correctly.

### More Content

Some other content.

### Summary

This is a somewhat long paragraph that is going to be duplicated later in the file.
We need to make sure the hashing logic catches it correctly.
"""
    issues = detect_duplicate_content(content)
    assert len(issues) == 1
    assert issues[0].issue_type == "duplicate_content"

def test_markdown_validator_ignores_short_duplicates():
    content = """### Title 1
Short.

### Title 2
Short."""
    issues = detect_duplicate_content(content)
    assert len(issues) == 0
