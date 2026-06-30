import re

def normalize_heading(title: str) -> str:
    title = title.strip().lower()
    if title.startswith("#"):
        title = title.lstrip("#").strip()
    if ":" in title:
        title = title.split(":", 1)[0].strip()
    return title

def apply_section_patch(draft: str, heading: str, replacement_content: str) -> str:
    """
    Deterministically replaces a section of markdown content under a specific heading.
    A section includes the heading itself and all content (including lower-level subheadings)
    up to the next heading of equal or higher level.
    """
    lines = draft.splitlines()
    
    target_heading = heading.strip().lower()
    if target_heading.startswith("#"):
        target_heading = target_heading.lstrip("#").strip()
    
    from src.utils.markdown_parser import parse_markdown_lines
    
    start_idx = -1
    start_level = -1
    heading_line = ""
    
    parsed_lines = list(parse_markdown_lines(draft))
    
    for parsed in parsed_lines:
        if parsed.is_heading and not parsed.is_inside_fence:
            if normalize_heading(parsed.heading_title) == normalize_heading(target_heading):
                start_idx = parsed.line_number - 1 # 0-indexed
                start_level = parsed.heading_level
                heading_line = parsed.original_line
                break
                
    if start_idx == -1:
        raise ValueError(f"Heading '{heading}' not found in draft.")
        
    # Look for the end of the section (next heading with equal or higher level, i.e., <= start_level hashes)
    end_idx = len(lines)
    for parsed in parsed_lines[start_idx + 1:]:
        if parsed.is_heading and not parsed.is_inside_fence:
            if parsed.heading_level <= start_level:
                end_idx = parsed.line_number - 1
                break
                
    before_part = lines[:start_idx]
    after_part = lines[end_idx:]
    
    # If the LLM included the heading in the replacement_content, remove it to avoid duplication.
    # We check if the first non-empty line in replacement_content is the heading.
    import re
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
    replacement_lines = replacement_content.strip().splitlines()
    if replacement_lines:
        first_line = replacement_lines[0].strip()
        first_line_match = heading_pattern.match(first_line)
        if first_line_match:
            first_heading_text = first_line_match.group(2).strip().lower()
            if normalize_heading(first_heading_text) == normalize_heading(target_heading):
                # Remove the duplicate heading from the replacement content
                replacement_lines = replacement_lines[1:]
    
    clean_replacement = "\n".join(replacement_lines).strip()
    
    # Standardize spacing by putting one newline after the heading
    middle = heading_line + "\n\n" + clean_replacement if clean_replacement else heading_line
    
    # Reassemble
    before_str = "\n".join(before_part)
    after_str = "\n".join(after_part)
    
    parts = []
    if before_str:
        parts.append(before_str)
    parts.append(middle)
    if after_str:
        parts.append(after_str)
        
    result = "\n".join(parts)
    
    # Preserve trailing newline if draft had it
    if draft.endswith("\n") and not result.endswith("\n"):
        result += "\n"
        
    return result
