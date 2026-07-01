import re

# Standalone markers that are always blocked
TODO_STANDALONE = re.compile(r"^(?:#|\/\/|\/\*|<!--|\s)*TODO(?:\s*:\s*.*)?$|^\s*TODO\s*$|^\s*\[TODO\]\s*$|^\s*\{\{TODO\}\}\s*$")
TBD_STANDALONE = re.compile(r"^\s*TBD\s*$|^\s*\[TBD\]\s*$|^\s*TBD\s*:\s*.*$")

# General brackets matching
BRACKET_RE = re.compile(r"\[([^\]]+)\]")

TEMPLATE_KEYWORDS = [
    "prompt template",
    "diagnostic prompt",
    "example prompt",
    "fill-in prompt",
    "learner template",
    "debugging request template",
    "use this structure",
    "copy this structure",
    "fill in this template",
    "template for asking",
    "template",
    "example",
    "prompt",
    "instruction",
    "structure",
    "snippet"
]

INSTRUCTIONAL_KEYWORDS = [
    "avoid", "remove", "clean", "hygiene", "cleanup", "example", 
    "template", "prompt", "explain", "explanation", "tutorial", 
    "guide", "debugging", "paste", "snippet", "comment", "anti-pattern"
]

def has_template_context(context_lines: list[str]) -> bool:
    for line in context_lines:
        line_lower = line.lower()
        if any(k in line_lower for k in TEMPLATE_KEYWORDS):
            return True
    return False

def classify_placeholder(line: str, context_lines: list[str]) -> dict:
    line_lower = line.lower()
    line_stripped = line.strip()
    
    # 1. Standalone TODO is always blocked
    if TODO_STANDALONE.match(line_stripped):
        return {
            "is_blocked": True,
            "matched_term": line_stripped,
            "rule_id": "unresolved_standalone_todo",
            "reason": "Standalone unresolved TODO marker"
        }
        
    # 2. TODO directive (non-instructional) is always blocked
    if "todo:" in line_lower and len(line_stripped) < 150:
        is_instructional = any(k in line_lower for k in INSTRUCTIONAL_KEYWORDS)
        if not is_instructional:
            return {
                "is_blocked": True,
                "matched_term": line_stripped,
                "rule_id": "unresolved_todo_directive",
                "reason": "Unresolved TODO directive in final content"
            }
            
    # 3. TBD standalone is always blocked
    if TBD_STANDALONE.match(line_stripped):
        return {
            "is_blocked": True,
            "matched_term": line_stripped,
            "rule_id": "unresolved_tbd",
            "reason": "Standalone unresolved TBD marker"
        }
        
    # 4. Bracketed texts (both Insert/Placeholder/TBD style and general uppercase slots)
    bracket_matches = BRACKET_RE.findall(line)
    for match_text in bracket_matches:
        full_match = f"[{match_text}]"
        match_lower = match_text.lower().strip()
        
        # Hard exclusions that are never allowed, even inside templates
        if match_lower in ["todo", "tbd", "insert", "placeholder"]:
            return {
                "is_blocked": True,
                "matched_term": full_match,
                "rule_id": "unresolved_bracket_placeholder",
                "reason": f"Unresolved {match_lower} placeholder"
            }
            
        # For other bracketed texts, check if there is a template context nearby
        if has_template_context(context_lines):
            continue
        else:
            return {
                "is_blocked": True,
                "matched_term": full_match,
                "rule_id": "unresolved_bracket_placeholder",
                "reason": "Unresolved bracket placeholder"
            }
            
    # 5. Missing content phrases
    missing_content_phrases = ["coming soon", "fill this in", "replace this", "add details here"]
    for phrase in missing_content_phrases:
        if phrase in line_lower and len(line_stripped) < 100:
            return {
                "is_blocked": True,
                "matched_term": phrase,
                "rule_id": "missing_content_placeholder",
                "reason": f"Unresolved placeholder phrase '{phrase}'"
            }
            
    # 6. Generic mock phrases
    generic_placeholders = [
        "mocked response",
        "this is a mock core concepts",
        "this is a mock practical application",
        "socratic ed-forge is great",
        "lorem ipsum"
    ]
    for p in generic_placeholders:
        if p in line_lower:
            return {
                "is_blocked": True,
                "matched_term": p,
                "rule_id": "mock_leakage",
                "reason": f"Mocked text leakage '{p}'"
            }
            
    return {"is_blocked": False}
