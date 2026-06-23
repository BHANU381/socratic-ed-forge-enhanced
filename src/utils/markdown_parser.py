from dataclasses import dataclass
from typing import List, Optional, Iterator
import re

@dataclass
class MarkdownHeading:
    level: int
    title: str
    line_number: int

@dataclass
class ParsedLine:
    line_number: int
    original_line: str
    is_heading: bool
    heading_level: Optional[int]
    heading_title: Optional[str]
    is_inside_fence: bool
    is_malformed_heading: bool

def parse_markdown_lines(markdown: str) -> Iterator[ParsedLine]:
    """
    Parses a markdown string line by line, maintaining state for fenced code blocks.
    Identifies proper Markdown headings and malformed headings outside of fenced code.
    """
    lines = markdown.splitlines()
    inside_fence = False
    fence_marker = None
    
    valid_heading_re = re.compile(r"^(#{1,6})\s+(.+)$")
    malformed_heading_re = re.compile(r"^#+[^#\s]")
    
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        
        # Check for fence markers
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not inside_fence:
                inside_fence = True
                fence_marker = stripped[:3]
            elif stripped.startswith(fence_marker):
                inside_fence = False
                fence_marker = None
            
            yield ParsedLine(i, line, False, None, None, True, False)
            continue
            
        if inside_fence:
            yield ParsedLine(i, line, False, None, None, True, False)
            continue
            
        # We are outside a code fence, so check for headings
        match = valid_heading_re.match(stripped)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            yield ParsedLine(i, line, True, level, title, False, False)
        elif malformed_heading_re.match(stripped):
            yield ParsedLine(i, line, False, None, None, False, True)
        else:
            yield ParsedLine(i, line, False, None, None, False, False)

def extract_headings_outside_fences(markdown: str) -> List[MarkdownHeading]:
    """
    Returns a list of clean MarkdownHeadings, completely ignoring anything inside code fences.
    """
    headings = []
    for parsed in parse_markdown_lines(markdown):
        if parsed.is_heading:
            headings.append(MarkdownHeading(
                level=parsed.heading_level,
                title=parsed.heading_title,
                line_number=parsed.line_number
            ))
    return headings
