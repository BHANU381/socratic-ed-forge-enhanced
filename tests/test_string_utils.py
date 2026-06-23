import pytest
from src.utils.string_utils import normalize_module_heading, normalize_submodule_heading

def test_normalize_module_heading():
    assert normalize_module_heading("Module 1: Getting Started") == "Getting Started"
    assert normalize_module_heading("# Module 1: Getting Started") == "Getting Started"
    assert normalize_module_heading("### module 2 - Deep Dive") == "Deep Dive"
    assert normalize_module_heading("Getting Started") == "Getting Started"

def test_normalize_submodule_heading():
    assert normalize_submodule_heading("Submodule 1: Variables") == "Variables"
    assert normalize_submodule_heading("## Submodule 1: Variables") == "Variables"
    assert normalize_submodule_heading("Variables") == "Variables"

def test_normalize_step_headings():
    from src.utils.string_utils import normalize_step_headings
    
    draft = """### Practical Application

Some intro text.

### Step 1: Initialization

Do this.

### Exercise 2: Build it

Do that.

### Summary and Key Takeaways

End of lesson.
"""
    
    expected = """### Practical Application

Some intro text.

#### Step 1: Initialization

Do this.

#### Exercise 2: Build it

Do that.

### Summary and Key Takeaways

End of lesson.
"""
    # Should demote Step 1 and Exercise 2 because they are inside Practical Application
    # and they match the step-like keyword list. Summary should remain untouched.
    assert normalize_step_headings(draft) == expected

    # Test it doesn't touch things outside known section boundaries
    draft_no_parent = """### Step 1: Alone

This should not be demoted because it isn't inside a parent section.
"""
    assert normalize_step_headings(draft_no_parent) == draft_no_parent

    # Test with known_sections to ensure we only demote inside known boundaries
    # Test with known_sections to ensure we only demote inside known boundaries
    draft_with_unknown_sections = """### Practical Application
Some intro.

### Step 1: Inside

Do this.

### Random Unknown Section

More text.

### Step 2: Outside

Do that.
"""
    expected_with_unknown = """### Practical Application
Some intro.

#### Step 1: Inside

Do this.

### Random Unknown Section

More text.

### Step 2: Outside

Do that.
"""
    assert normalize_step_headings(draft_with_unknown_sections, known_sections=["Practical Application"]) == expected_with_unknown

def test_normalize_step_headings_ignores_fenced_code_comments():
    from src.utils.string_utils import normalize_step_headings
    draft = """### Known Section
Intro
```python
### Step 1: Inside Code
print(1)
```
### Another Known Section
"""
    known_sections = ["Known Section", "Another Known Section"]
    # If the parser breaks on `### Step 1: Inside Code`, it will erroneously demote it to `#### Step 1: Inside Code`
    normalized = normalize_step_headings(draft, known_sections)
    assert "#### Step 1: Inside Code" not in normalized
    assert "### Step 1: Inside Code" in normalized
