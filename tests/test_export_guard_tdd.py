import pytest
import re
from unittest.mock import MagicMock
from src.engine.orchestrator import check_manifest_and_leakage

# Mock course configuration helper
def make_mock_course():
    mod1 = MagicMock()
    mod1.module_title = "Module 1: Test Module"
    topic1 = MagicMock()
    topic1.topic_title = "1.1 Setup"
    mod1.topics = [topic1]
    
    course = MagicMock()
    course.modules = [mod1]
    return course

# =====================================================================
# Test Group A: Real placeholder blockers
# =====================================================================

def test_real_placeholder_blockers():
    course = make_mock_course()
    
    # 1. Standalone TODO
    content1 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nTODO"
    err1 = check_manifest_and_leakage(content1, course)
    assert err1 is not None
    assert "TODO" in err1
    
    # 2. TODO: finish this section
    content2 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nTODO: finish this section"
    err2 = check_manifest_and_leakage(content2, course)
    assert err2 is not None
    
    # 3. [TODO]
    content3 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\n[TODO]"
    err3 = check_manifest_and_leakage(content3, course)
    assert err3 is not None
    
    # 4. {{TODO}}
    content4 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\n{{TODO}}"
    err4 = check_manifest_and_leakage(content4, course)
    assert err4 is not None
    
    # 5. [Insert content here]
    content5 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\n[Insert content here]"
    err5 = check_manifest_and_leakage(content5, course)
    assert err5 is not None
    
    # 6. [Insert Code Here]
    content6 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\n[Insert Code Here]"
    err6 = check_manifest_and_leakage(content6, course)
    assert err6 is not None
    
    # 7. TBD as standalone content
    content7 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nTBD"
    err7 = check_manifest_and_leakage(content7, course)
    assert err7 is not None
    
    # 8. Lorem ipsum
    content8 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nLorem ipsum dolor sit amet"
    err8 = check_manifest_and_leakage(content8, course)
    assert err8 is not None


# =====================================================================
# Test Group B: Instructional mentions allowed
# =====================================================================

def test_instructional_mentions_allowed():
    course = make_mock_course()
    
    # 1. Prose sentence
    content1 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nAvoid TODO comments in production code."
    assert check_manifest_and_leakage(content1, course) is None
    
    # 2. PR cleanup
    content2 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nRemove todo-style placeholders before committing."
    assert check_manifest_and_leakage(content2, course) is None
    
    # 3. Explain failure modes
    content3 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nThe AI may leave TODO comments in generated code."
    assert check_manifest_and_leakage(content3, course) is None
    
    # 4. Planning list
    content4 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nA todo list can help during planning."
    assert check_manifest_and_leakage(content4, course) is None
    
    # 5. Instructional guidance
    content5 = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nThis is an example of a bad placeholder."
    assert check_manifest_and_leakage(content5, course) is None


# =====================================================================
# Test Group C: Code block context
# =====================================================================

def test_code_block_context():
    course = make_mock_course()
    
    # 1. Under "Bad Example"
    content1 = """# Module 1: Test Module
## Submodule: 1.1 Setup
### Bad Example
```python
# TODO: implement this
```
"""
    assert check_manifest_and_leakage(content1, course) is None
    
    # 2. Under "Anti-pattern"
    content2 = """# Module 1: Test Module
## Submodule: 1.1 Setup
### Anti-pattern
```python
# TODO: remove this
```
"""
    assert check_manifest_and_leakage(content2, course) is None
    
    # 3. Under "Before Cleanup"
    content3 = """# Module 1: Test Module
## Submodule: 1.1 Setup
### Before Cleanup
```python
# TODO: fix this
```
"""
    assert check_manifest_and_leakage(content3, course) is None
    
    # 4. Standard Implementation code block containing unfinished TODO should block
    content4 = """# Module 1: Test Module
## Submodule: 1.1 Setup
### Standard Code Example
```python
# TODO: implement real logic
```
"""
    assert check_manifest_and_leakage(content4, course) is not None
    
    # 5. Standard Code Block with [Insert Code Here] should block
    content5 = """# Module 1: Test Module
## Submodule: 1.1 Setup
### Solution
```python
[Insert Code Here]
```
"""
    assert check_manifest_and_leakage(content5, course) is not None


# =====================================================================
# Test Group D: Scan source isolation
# =====================================================================

def test_scan_source_isolation():
    course = make_mock_course()
    
    # The final markdown is clean, but strings are present in logs
    logs_content = "Export Guard Blocked Export: Contains placeholder: 'todo'"
    clean_markdown = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nReal content only."
    
    # Scanned content is just the markdown string passed to the check, not logs
    assert check_manifest_and_leakage(clean_markdown, course) is None


# =====================================================================
# Test Group E: Diagnostic logging
# =====================================================================

def test_diagnostic_logging():
    course = make_mock_course()
    content = "# Module 1: Test Module\n## Submodule: 1.1 Setup\nTODO: finish this section"
    
    err = check_manifest_and_leakage(content, course)
    assert err is not None
    # Blocked message includes matched term, line number, snippet, and rule id / description
    assert "TODO: finish this section" in err
    assert "Line: 3" in err or "line 3" in err.lower()
    assert "Rule:" in err or "rule" in err.lower()
