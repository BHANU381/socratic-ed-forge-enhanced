import pytest
from src.utils.markdown_parser import parse_markdown_lines, MarkdownHeading, ParsedLine

def test_parse_markdown_lines_tracks_fence():
    content = """# Real Heading

```python
# Fake Heading Inside Fence
### Another Fake Heading
```

## Another Real Heading
"""
    lines = list(parse_markdown_lines(content))
    
    # Line 1: # Real Heading
    assert lines[0].is_heading is True
    assert lines[0].heading_level == 1
    assert lines[0].is_inside_fence is False
    
    # Line 3: ```python
    assert lines[2].is_inside_fence is True
    
    # Line 4: # Fake Heading Inside Fence
    assert lines[3].is_heading is False
    assert lines[3].is_inside_fence is True
    
    # Line 5: ### Another Fake Heading
    assert lines[4].is_heading is False
    assert lines[4].is_inside_fence is True
    
    # Line 8: ## Another Real Heading
    assert lines[7].is_heading is True
    assert lines[7].heading_level == 2
    assert lines[7].is_inside_fence is False
