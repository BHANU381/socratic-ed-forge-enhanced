import os
import json
import datetime
import glob
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

ERROR_DIR = os.path.join(PROJECT_ROOT, 'data', 'learning_loop', 'errors')
FIX_DIR = os.path.join(PROJECT_ROOT, 'data', 'learning_loop', 'fixes')
STYLE_GUIDE_FILE = os.path.join(PROJECT_ROOT, 'data', 'learning_loop', 'style_guide.json')

def clear_style_guide():
    if os.path.exists(STYLE_GUIDE_FILE):
        try:
            os.remove(STYLE_GUIDE_FILE)
        except Exception as e:
            print(f"Error removing style guide: {e}")

def save_style_guide_rule_internal(new_rule_text, synthesizer):
    os.makedirs(os.path.dirname(STYLE_GUIDE_FILE), exist_ok=True)
    
    rules = []
    if os.path.exists(STYLE_GUIDE_FILE):
        try:
            with open(STYLE_GUIDE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rules = data.get("rules", [])
        except Exception as e:
            print(f"Error reading style guide file: {e}")
            
    existing_texts = [r["text"] for r in rules]
    matched_text = synthesizer.find_duplicate_rule(existing_texts, new_rule_text)
    
    timestamp = datetime.datetime.now().isoformat()
    
    if matched_text != "NEW":
        for r in rules:
            if r["text"] == matched_text:
                r["count"] = r.get("count", 0) + 1
                r["last_updated"] = timestamp
                break
    else:
        rule_id = f"rule_{len(rules) + 1:02d}"
        rules.append({
            "id": rule_id,
            "text": new_rule_text,
            "count": 1,
            "last_updated": timestamp
        })
        
    with open(STYLE_GUIDE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"rules": rules}, f, indent=4)

def is_noisy_error(error_text: str) -> bool:
    err = error_text.lower()
    # word-count complaints
    if "word-count" in err or "word count" in err or "words" in err or "600-word" in err or "600 word" in err or "600" in err:
        return True
    # target-depth or requirements
    if "target_words" in err or "target words" in err or "too short" in err or "minimum requirement" in err or "mandatory minimum" in err or "length_constraint" in err or "word_count_insufficient" in err or "required depth" in err:
        return True
    # arbitrary lesson-duration complaints / 30-40 minute lesson expectations
    if "duration" in err or "30-40" in err or "30–40" in err or "minute" in err:
        return True
    # heading structure complaints when deterministic validation passed
    if "heading" in err or "hierarchy" in err or "nesting" in err or "structure" in err:
        return True
    # patch editor execution failures
    if "patch editor" in err or "execution failure" in err or "failed to find" in err or "heading not found" in err:
        return True
    # semantic evaluator uncertainty
    if "uncertainty" in err or "not sure" in err or "uncertain" in err:
        return True
    return False

def record_lesson(module, submodule, error_text, fixed_content):
    """
    Records a 'lesson' by generating a style-guide rule and updating the centralized rulebook.
    """
    if is_noisy_error(error_text):
        print(f"LearningEngine: Skipped learning noisy error pattern: '{error_text}'")
        return "skipped"

    # Local import to prevent circular dependency
    from src.agents.core import StyleSynthesizer
    
    synthesizer = StyleSynthesizer()
    new_rule_text = synthesizer.synthesize_rule(error_text, fixed_content)
    
    save_style_guide_rule_internal(new_rule_text, synthesizer)
    
    # Return a mock safe_id for compatibility
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_id = f"{module}_{submodule}_{timestamp}"
    safe_id = re.sub(r'[<>:"/\\|?*&]', '_', raw_id)
    return safe_id

def get_learned_lessons():
    """
    Scans the style_guide.json file and returns the top 10 rules
    formatted as a clean bulleted list.
    """
    # migrate_old_lessons_if_needed()
    
    if not os.path.exists(STYLE_GUIDE_FILE):
        return ""
        
    try:
        with open(STYLE_GUIDE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            rules = data.get("rules", [])
    except Exception as e:
        print(f"Error reading style guide: {e}")
        return ""
        
    if not rules:
        return ""
        
    # Sort rules by count (descending) and last_updated (descending)
    rules.sort(key=lambda x: (x.get("count", 1), x.get("last_updated", "")), reverse=True)
    
    top_rules = rules[:10]
    rules_str = "\n".join([f"- {r['text']}" for r in top_rules])
    return rules_str
