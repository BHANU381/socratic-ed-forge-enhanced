import pytest
from src.utils.patch_utils import apply_section_patch

def test_apply_section_patch_basic():
    draft = """# Introduction
Old intro content.
# Exercises
Old exercises content.
"""
    # Replace Exercises section
    updated = apply_section_patch(draft, "Exercises", "New exercises content with more words.")
    expected = """# Introduction
Old intro content.
# Exercises

New exercises content with more words.
"""
    assert updated.strip() == expected.strip()

def test_apply_section_patch_with_subheadings():
    draft = """# Introduction
Old intro.
## Subsection
Some sub info.
# Exercises
Exercises.
"""
    # Replacing Introduction should replace Subsection as well (since it is a subheading of Introduction)
    updated = apply_section_patch(draft, "Introduction", "New intro content.\nNo subheadings anymore.")
    expected = """# Introduction

New intro content.
No subheadings anymore.
# Exercises
Exercises.
"""
    assert updated.strip() == expected.strip()

def test_apply_section_patch_heading_not_found():
    draft = """# Introduction
Intro content.
"""
    with pytest.raises(ValueError) as exc_info:
        apply_section_patch(draft, "Exercises", "New exercises.")
    assert "not found" in str(exc_info.value).lower()

def test_apply_section_patch_ignores_fenced_code_comments():
    draft = """# Target Section
Some text here.
```python
# Another Section
print("This should not end the target section extraction")
```
More text in the target section.

# Real Next Section
End of file.
"""
    # Replacing Target Section should not truncate at `# Another Section`
    updated = apply_section_patch(draft, "Target Section", "New replacement.")
    expected = """# Target Section

New replacement.
# Real Next Section
End of file.
"""
    assert updated.strip() == expected.strip()
