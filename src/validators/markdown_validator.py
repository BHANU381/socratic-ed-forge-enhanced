import re
from src.models.schemas import ValidationResult, ValidationIssue

def validate_markdown_structure(content: str) -> ValidationResult:
    issues = []
    detected_headings = []
    
    # 1. Unclosed code block validation
    lines = content.splitlines()
    in_code_block = False
    code_block_start_line = -1
    
    for idx, line in enumerate(lines):
        # We look for lines starting with ```
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                code_block_start_line = idx + 1
                
    if in_code_block:
        issues.append(ValidationIssue(
            severity="blocker",
            issue_type="unclosed_code_fence",
            message=f"Unclosed code fence starting at line {code_block_start_line}.",
            section=None
        ))
        
    # 2. Placeholders validation (TODO, [Insert ...], [Placeholder ...], mock content)
    placeholder_patterns = [
        (re.compile(r"(?i)\bTODO\b"), "TODO marker found"),
        (re.compile(r"(?i)\bTBD\b"), "TBD marker found"),
        (re.compile(r"(?i)\[Insert\s+[^\]]+\]"), "Insert placeholder found"),
        (re.compile(r"(?i)\[Placeholder\s+[^\]]+\]"), "Placeholder found"),
        (re.compile(r"(?i)\[insert\]"), "Insert placeholder found"),
        (re.compile(r"(?i)mocked response"), "Mocked Response found"),
        (re.compile(r"(?i)this is a mock core concepts"), "Mock Core Concepts found"),
        (re.compile(r"(?i)this is a mock practical application"), "Mock Practical Application found"),
        (re.compile(r"(?i)socratic ed-forge is great"), "Mock System Promo found"),
        (re.compile(r"(?i)lorem ipsum"), "Lorem Ipsum text found")
    ]
    
    known_vars = {
        "learner_level", "code_example_style", "explanation_depth", "quality_profile",
        "lesson_contract", "draft", "learned_rules", "module_context", "content_context",
        "running_summary", "validator_errors", "semantic_feedback", "patch_instruction",
        "target_heading", "course_name", "course_topic", "duration_weeks", "module_title",
        "sub_title", "submodule_title"
    }
    var_re = re.compile(r"\{([a-zA-Z0-9_]+)\}")
    
    from src.utils.markdown_parser import parse_markdown_lines
    
    def classify_placeholder_occurrence(parsed_line, context_lines, rule_id=None):
        if parsed_line.is_inside_fence:
            return "allowed"
        
        line_lower = parsed_line.original_line.lower().strip()
        
        # Check blockquotes or quotes
        if line_lower.startswith(">") or (line_lower.startswith('"') and line_lower.endswith('"')) or (line_lower.startswith("'") and line_lower.endswith("'")):
            return "warning"
            
        if rule_id in ["unresolved_standalone_todo", "unresolved_todo_directive", "unresolved_tbd", "unresolved_bracket_placeholder", "missing_content_placeholder"]:
            return "blocker"
            
        # Instructional keywords
        instructional_keywords = [
            "avoid", "remove", "clean", "hygiene", "cleanup", "example", 
            "template", "prompt", "explain", "explanation", "tutorial", 
            "guide", "debugging", "paste", "snippet", "comment", "anti-pattern"
        ]
        
        if any(k in line_lower for k in instructional_keywords):
            return "warning"
        
        # Check context window for template indicators
        for ctx_line in context_lines:
            ctx_lower = ctx_line.original_line.lower()
            if any(k in ctx_lower for k in instructional_keywords):
                return "warning"
                
        return "blocker"
        
    parsed_lines = list(parse_markdown_lines(content))
    context_window = []
    
    for parsed in parsed_lines:
        # Maintain context window of last 14 lines
        context_window.append(parsed)
        if len(context_window) > 15:
            context_window.pop(0)
            
        line = parsed.original_line
        
        # Check placeholders
        from src.utils.placeholder_classifier import classify_placeholder
        ctx_strings = [p.original_line for p in context_window[:-1]]
        res_class = classify_placeholder(line, ctx_strings)
        if res_class.get("is_blocked"):
            severity = classify_placeholder_occurrence(parsed, context_window[:-1], res_class.get("rule_id"))
            if severity != "allowed":
                issues.append(ValidationIssue(
                    severity=severity,
                    issue_type="placeholder",
                    message=f"{res_class['reason']} at line {parsed.line_number}: '{line.strip()}'",
                    section=None
                ))
                    
        # Check unresolved variables
        for m in var_re.finditer(line):
            var_name = m.group(1)
            if var_name in known_vars:
                severity = classify_placeholder_occurrence(parsed, context_window[:-1])
                if severity != "allowed":
                    issues.append(ValidationIssue(
                        severity=severity,
                        issue_type="unresolved_variable",
                        message=f"Unresolved prompt variable '{var_name}' found at line {parsed.line_number}.",
                        section=None
                    ))
    
    active_headings = [] # list of dicts {"level": int, "name": str, "line": int, "has_content": bool}
    
    for parsed in parsed_lines:
        if parsed.is_malformed_heading and not parsed.is_inside_fence:
            issues.append(ValidationIssue(
                severity="warning",
                issue_type="malformed_heading",
                message=f"Malformed heading structure at line {parsed.line_number}: '{parsed.original_line.strip()}' (missing space after #)",
                section=None
            ))
            # Treat malformed heading as content for parent sections
            for ah in active_headings:
                ah["has_content"] = True
        else:
            if parsed.is_heading and not parsed.is_inside_fence:
                level = parsed.heading_level
                name = parsed.heading_title
                
                new_active = []
                for ah in active_headings:
                    if level <= ah["level"]:
                        if not ah["has_content"]:
                            issues.append(ValidationIssue(
                                severity="blocker",
                                issue_type="empty_section",
                                message=f"Section '{ah['name']}' starting at line {ah['line']} is empty.",
                                section=ah['name']
                            ))
                    else:
                        # Child heading indicates parent is not empty
                        ah["has_content"] = True
                        new_active.append(ah)
                        
                new_active.append({"level": level, "name": name, "line": parsed.line_number, "has_content": False})
                active_headings = new_active
                detected_headings.append(name)
            elif parsed.original_line.strip():
                # Any content (including lines inside fences) counts as content for the active heading
                for ah in active_headings:
                    ah["has_content"] = True

    for ah in active_headings:
        if not ah["has_content"]:
            issues.append(ValidationIssue(
                severity="blocker",
                issue_type="empty_section",
                message=f"Section '{ah['name']}' starting at line {ah['line']} is empty.",
                section=ah['name']
            ))
        
    dup_issues = detect_duplicate_content(content)
    issues.extend(dup_issues)
                
    passed = not any(i.severity == "blocker" for i in issues)
    
    return ValidationResult(
        passed=passed,
        issues=issues,
        detected_headings=detected_headings
    )

import hashlib

def detect_duplicate_content(content: str) -> list[ValidationIssue]:
    issues = []
    # Normalize line endings and split by 2 or more newlines
    normalized_content = content.replace("\r\n", "\n")
    blocks = re.split(r'\n\s*\n', normalized_content)
    seen_hashes = {}
    
    for block in blocks:
        clean_block = block.strip()
        # Only check blocks of significant size to avoid flagging short lines or simple titles
        if len(clean_block) > 50:
            block_hash = hashlib.md5(clean_block.encode('utf-8')).hexdigest()
            if block_hash in seen_hashes:
                issues.append(ValidationIssue(
                    severity="blocker",
                    issue_type="duplicate_content",
                    message=f"Duplicate content block detected: '{clean_block[:40]}...'",
                    section=None
                ))
            else:
                seen_hashes[block_hash] = True
    return issues
