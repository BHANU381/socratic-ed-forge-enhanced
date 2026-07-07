import re
from src.models.schemas import LessonContract, ValidationResult, ValidationIssue

def validate_lesson_contract(content: str, contract: LessonContract) -> ValidationResult:
    issues = []
    
    # 1. Parse markdown lines to extract sections and their text
    from src.utils.markdown_parser import parse_markdown_lines
    
    sections_content = {}
    sections_heading_level = {}
    all_headings_level = {}
    current_parent_heading = None
    current_parent_level = 0
    detected_headings = []
    heading_level_counts = {}
    
    for parsed in parse_markdown_lines(content):
        if parsed.is_heading and not parsed.is_inside_fence:
            level = parsed.heading_level
            heading_text = parsed.heading_title
            heading_lower = heading_text.lower()
            detected_headings.append(heading_text)
            all_headings_level[heading_lower] = level
            
            heading_level_counts[level] = heading_level_counts.get(level, 0) + 1
            
            if current_parent_heading is None or level <= current_parent_level:
                # New parent section
                current_parent_heading = heading_text.lower()
                current_parent_level = level
                sections_content[current_parent_heading] = []
                sections_heading_level[current_parent_heading] = level
            else:
                # Child heading, belongs to current parent
                if current_parent_heading is not None:
                    # Still need to include the text of the child heading itself in word count!
                    sections_content[current_parent_heading].append(parsed.original_line)
        else:
            if current_parent_heading is not None:
                sections_content[current_parent_heading].append(parsed.original_line)
                
    # Calculate word count and usefulness for each section
    sections_word_count = {}
    sections_usefulness = {}
    
    code_fence_re = re.compile(r"^```")
    usefulness_pattern = re.compile(r"(?i)^(-|\*|\d+\.)\s+(Step|Task|Exercise)|^(Step|Part|Exercise)\b|\|.+\|.+\|")
    
    for heading, text_lines in sections_content.items():
        has_usefulness = False
        in_code_block = False
        prose_words = []
        
        for line in text_lines:
            stripped = line.strip()
            if code_fence_re.match(stripped):
                has_usefulness = True
                in_code_block = not in_code_block
                continue
                
            if in_code_block:
                continue
                
            if usefulness_pattern.search(stripped):
                has_usefulness = True
                
            words = [w for w in stripped.split() if w]
            prose_words.extend(words)
            
        sections_word_count[heading] = len(prose_words)
        sections_usefulness[heading] = has_usefulness
        
    # 2. Match contract requirements against parsed headings
    for req in contract.sections:
        # Construct possible matching strings
        target_names = {req.title.lower()}
        for alias in req.aliases:
            target_names.add(alias.lower())
            
        matched_heading_normalized = None
        matched_word_count = 0
        
        # Look for a match in our parsed sections
        for heading in sections_word_count:
            # Check exact match or prefix match with colon/dash
            is_match = heading in target_names
            if not is_match:
                for target in target_names:
                    if heading.startswith(target + ":") or heading.startswith(target + " -"):
                        is_match = True
                        break
                        
            if is_match:
                matched_heading_normalized = heading
                matched_word_count = sections_word_count[heading]
                break
                
        if matched_heading_normalized is None:
            # Maybe it's a child heading? Check all_headings_level
            found_child_normalized = None
            for heading in all_headings_level:
                is_match = heading in target_names
                if not is_match:
                    for target in target_names:
                        if heading.startswith(target + ":") or heading.startswith(target + " -"):
                            is_match = True
                            break
                if is_match:
                    found_child_normalized = heading
                    break
            
            if found_child_normalized is None:
                if req.required:
                    issues.append(ValidationIssue(
                        severity="blocker",
                        issue_type="missing_section",
                        message=f"Required section '{req.title}' is missing.",
                        section=req.title
                    ))
            else:
                actual_level = all_headings_level[found_child_normalized]
                if req.required_level is not None and actual_level != req.required_level:
                    issues.append(ValidationIssue(
                        severity="blocker",
                        issue_type="invalid_heading_level",
                        message=f"Section '{req.title}' expected heading level {req.required_level}, but found level {actual_level}.",
                        section=req.title
                    ))
        else:
            actual_level = sections_heading_level.get(matched_heading_normalized)
            if req.required_level is not None and actual_level != req.required_level:
                issues.append(ValidationIssue(
                    severity="blocker",
                    issue_type="invalid_heading_level",
                    message=f"Section '{req.title}' expected heading level {req.required_level}, but found level {actual_level}.",
                    section=req.title
                ))
                
            target_val = getattr(req, "target_words", None)
            min_val = req.min_words
            
            if min_val is not None:
                has_usefulness = sections_usefulness.get(matched_heading_normalized, False)
                target = target_val if target_val is not None else min_val
                
                raw_text = "".join(sections_content.get(matched_heading_normalized, [])).strip()
                is_placeholder = bool(re.match(r"^\[?placeholder\]?$", raw_text, re.IGNORECASE))
                
                if is_placeholder:
                    pass
                elif matched_word_count == 0 and not has_usefulness:
                    issues.append(ValidationIssue(
                        severity="blocker",
                        issue_type="empty_section",
                        message=f"Section '{req.title}' is empty.",
                        section=req.title
                    ))
                elif matched_word_count < min_val:
                    if matched_word_count < (min_val * 0.5) and not has_usefulness:
                        severity = "blocker"
                    else:
                        severity = "warning"
                    issues.append(ValidationIssue(
                        severity=severity,
                        issue_type="section_too_short",
                        message=f"Section '{req.title}' has {matched_word_count} words, which is below the minimum word count limit of {min_val} words. Useful elements: {has_usefulness}",
                        section=req.title
                    ))
                elif matched_word_count < target:
                    issues.append(ValidationIssue(
                        severity="warning",
                        issue_type="section_below_target",
                        message=f"Section '{req.title}' has {matched_word_count} words, which is below the target depth of {target} words.",
                        section=req.title
                    ))
                    
    # 3. Check global heading rules if present
    if contract.heading_rules and contract.heading_rules.main_content_heading:
        main_rule = contract.heading_rules.main_content_heading
        if main_rule.must_be_unique_per_submodule:
            count = heading_level_counts.get(main_rule.required_level, 0)
            if count > 1:
                issues.append(ValidationIssue(
                    severity="blocker",
                    issue_type="multiple_main_headings",
                    message=f"Submodule contains multiple level {main_rule.required_level} headings. The '{main_rule.canonical}' heading must be the ONLY level {main_rule.required_level} heading.",
                ))

    passed = not any(i.severity == "blocker" for i in issues)
    
    return ValidationResult(
        passed=passed,
        issues=issues,
        detected_headings=detected_headings
    )
