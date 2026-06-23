import pytest
from src.utils.cleanup_utils import final_markdown_cleanup

def test_final_markdown_cleanup_removes_duplicates():
    content = """# Module 1
## Submodule 1
This is a very informative paragraph about Python.
It has multiple sentences to make it long enough.

## Submodule 2
This is a very informative paragraph about Python.
It has multiple sentences to make it long enough.

Some other unique text.
"""
    cleaned = final_markdown_cleanup(content)
    
    # The duplicate block under Submodule 2 should be removed, but unique text stays.
    assert cleaned.count("This is a very informative paragraph about Python.") == 1
    assert "Some other unique text." in cleaned

def test_final_markdown_cleanup_ignores_short_lines():
    content = """# Intro
Yes.
# Outro
Yes."""
    cleaned = final_markdown_cleanup(content)
    assert cleaned.count("Yes.") == 2
