import re

def normalize_module_heading(title: str) -> str:
    """
    Strips 'Module X:' or '# Module X:' prefixes from module titles.
    """
    # Remove leading hashes
    title = re.sub(r'^#+\s*', '', title.strip())
    # Remove "Module X:" or "module X -"
    title = re.sub(r'(?i)^module\s*\d+\s*[:-]\s*', '', title)
    return title.strip()

def normalize_submodule_heading(title: str) -> str:
    """
    Strips 'Submodule X:' or '## Submodule X:' prefixes from submodule titles.
    """
    # Remove leading hashes
    title = re.sub(r'^#+\s*', '', title.strip())
    # Remove "Submodule X:" or "submodule X -"
    title = re.sub(r'(?i)^submodule\s*\d+\s*[:-]\s*', '', title)
    return title.strip()

from typing import List

def normalize_step_headings(draft: str, known_sections: List[str] = None) -> str:
    """
    Scans a draft for accidental same-level step headings inside sections.
    If a section like `### Practical Application` is followed by `### Step 1:`,
    the step label is demoted to `#### Step 1:` to preserve Markdown hierarchy.
    """
    if known_sections is None:
        known_sections = []
        
    lines = draft.replace('\r\n', '\n').split('\n')
    from src.utils.markdown_parser import parse_markdown_lines
    
    # Identify headings that should be treated as steps/activities
    step_pattern = re.compile(r"(?i)^(Step|Part|Level|Exercise|Activity|Example|Task|Checklist)\b")
    
    current_parent_level = None
    normalized_lines = []
    
    for parsed in parse_markdown_lines(draft.replace('\r\n', '\n')):
        if parsed.is_heading and not parsed.is_inside_fence:
            level = parsed.heading_level
            heading_text = parsed.heading_title
            
            is_step_heading = bool(step_pattern.match(heading_text))
            
            if is_step_heading and current_parent_level is not None and level == current_parent_level:
                # Demote the heading by adding one more '#'
                normalized_lines.append("#" + parsed.original_line)
            else:
                # Normal heading, update parent level if it's a known section
                if not is_step_heading:
                    # In production, headings might not perfectly match case. We should normalize case for comparison.
                    known_lower = [k.lower() for k in known_sections] if known_sections else []
                    if not known_lower or heading_text.lower() in known_lower:
                        current_parent_level = level
                    else:
                        # It's an unknown section, so stop tracking parent level 
                        # to avoid demoting steps outside known boundaries.
                        current_parent_level = None
                normalized_lines.append(parsed.original_line)
        else:
            normalized_lines.append(parsed.original_line)
            
    result = '\n'.join(normalized_lines)
    
    # Preserve trailing newline if draft had it
    if draft.endswith('\n') and not result.endswith('\n'):
        result += '\n'
        
    return result
