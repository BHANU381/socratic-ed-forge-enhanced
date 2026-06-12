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

def migrate_old_lessons_if_needed():
    if not os.path.exists(ERROR_DIR):
        return
    
    error_files = glob.glob(os.path.join(ERROR_DIR, "*_error.json"))
    if not error_files:
        return
        
    print(f"Found {len(error_files)} old experience replay lessons. Migrating to centralized style_guide.json...")
    
    # local import to avoid circular dependency
    from src.agents.core import StyleSynthesizer
    
    synthesizer = StyleSynthesizer()
    
    for error_file in error_files:
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                error_data = json.load(f)
            
            error_text = error_data.get("error", "")
            
            # Find the corresponding fix file
            lesson_id = os.path.basename(error_file).replace("_error.json", "")
            fix_file = os.path.join(FIX_DIR, f"{lesson_id}_fix.md")
            
            fixed_content = ""
            if os.path.exists(fix_file):
                with open(fix_file, 'r', encoding='utf-8') as f:
                    fixed_content = f.read()
            
            # Synthesize rule
            new_rule = synthesizer.synthesize_rule(error_text, fixed_content)
            
            # Save rule to style_guide.json
            save_style_guide_rule_internal(new_rule, synthesizer)
            
            # Delete old files
            os.remove(error_file)
            if os.path.exists(fix_file):
                os.remove(fix_file)
                
        except Exception as e:
            print(f"Error migrating {error_file}: {e}")

def record_lesson(module, submodule, error_text, fixed_content):
    """
    Records a 'lesson' by generating a style-guide rule and updating the centralized rulebook.
    """
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
    migrate_old_lessons_if_needed()
    
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
