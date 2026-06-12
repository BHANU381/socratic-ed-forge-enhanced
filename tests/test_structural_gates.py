import os
import pytest
from src.engine.orchestrator import normalize_draft, validate_draft

def test_normalize_draft_strips_invalid_elements():
    # Setup draft with illegal headings and repeated submodule titles
    draft = """
    
    # Module 1: Intro
    ## Submodule: 1.1 Topic Title
    
    ### 1.1 Topic Title
    
    ### Introduction
    This is introductory content.
    
    ### Core Concepts
    ### Core Concepts
    Some concepts.
    
    ### Practical Application
    Code exercise.
    
    ### Summary and Key Takeaways
    Concise points.
    """
    
    normalized = normalize_draft(draft, "1.1 Topic Title")
    
    # Assert module and submodule headers are stripped
    assert "# Module" not in normalized
    assert "## Submodule" not in normalized
    assert "### 1.1 Topic Title" not in normalized
    
    # Assert empty lines at start are cleaned
    assert normalized.startswith("### Introduction")
    
    # Assert duplicate adjacent headers are cleaned
    # Note: "### Core Concepts" followed by "### Core Concepts" is adjacent duplicate
    assert normalized.count("### Core Concepts") == 1
    
    # Assert normal structure remains
    assert "### Introduction" in normalized
    assert "### Core Concepts" in normalized
    assert "### Practical Application" in normalized
    assert "### Summary and Key Takeaways" in normalized

def test_validate_draft_valid():
    valid_draft = """### Introduction
Hook content.

### Core Concepts
Deep dive content.

### Practical Application
Hands-on task.

### Summary and Key Takeaways
takeaways list."""
    
    errors = validate_draft(valid_draft)
    assert len(errors) == 0

def test_validate_draft_invalid_headings():
    # Missing heading and wrong order
    invalid_draft_1 = """### Introduction
Hook content.

### Practical Application
Hands-on task.

### Core Concepts
Deep dive content.

### Summary and Key Takeaways
takeaways list."""
    
    errors = validate_draft(invalid_draft_1)
    assert any("wrong order" in e.lower() for e in errors)
    
    # Illegal high-level headings
    invalid_draft_2 = """# Module 1
### Introduction
Hook content.

### Core Concepts
Deep dive content.

### Practical Application
Hands-on task.

### Summary and Key Takeaways
takeaways list."""
    
    errors = validate_draft(invalid_draft_2)
    assert any("Found illegal header level" in e for e in errors)
    
    # Duplicate headings
    invalid_draft_3 = """### Introduction
Hook content.

### Core Concepts
Deep dive.

### Core Concepts
Deep dive 2.

### Practical Application
Hands-on.

### Summary and Key Takeaways
takeaways."""
    
    errors = validate_draft(invalid_draft_3)
    assert any("appears multiple times" in e for e in errors)
