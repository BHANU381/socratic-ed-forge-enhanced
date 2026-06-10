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

def record_lesson(module, submodule, error_text, fixed_content):
    """
    Records a 'lesson' by saving the error and the subsequent fix.
    This enables the agents to learn from past mistakes.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # SANITIZE THE ID: Remove all characters that are illegal in Windows filenames
    # This includes : * ? " < > | & etc.
    raw_id = f"{module}_{submodule}_{timestamp}"
    safe_id = re.sub(r'[<>:"/\\|?*&]', '_', raw_id)
    
    os.makedirs(ERROR_DIR, exist_ok=True)
    os.makedirs(FIX_DIR, exist_ok=True)
    
    error_file = os.path.join(ERROR_DIR, f"{safe_id}_error.json")
    fix_file = os.path.join(FIX_DIR, f"{safe_id}_fix.md")
    
    error_data = {
        "module": module,
        "submodule": submodule,
        "timestamp": timestamp,
        "error": error_text
    }
    
    with open(error_file, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, indent=4)
        
    with open(fix_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    return safe_id

def get_learned_lessons():
    """
    Scans the learning loop directory and returns a list of 'lessons'
    formatted as a string to be injected into agent prompts.
    """
    lessons_str = ""
    if not os.path.exists(ERROR_DIR):
        return ""
    
    # Get all error files, sorted by timestamp (newest first)
    error_files = sorted(glob.glob(os.path.join(ERROR_DIR, "*_error.json")), reverse=True)
    
    for error_file in error_files[:10]:
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                error_data = json.load(f)
            
            # Find the corresponding fix file
            lesson_id = os.path.basename(error_file).replace("_error.json", "")
            fix_file = os.path.join(FIX_DIR, f"{lesson_id}_fix.md")
            
            if os.path.exists(fix_file):
                with open(fix_file, 'r', encoding='utf-8') as f:
                    fixed_content = f.read()
                
                lessons_str += f"\n- [PREVIOUS ERROR in {error_data['module']} -> {error_data['submodule']}]: {error_data['error']}\n"
                lessons_str += f"  [CORRECTED VERSION]:\n{fixed_content}\n"
        except Exception as e:
            print(f"Error reading lesson {error_file}: {e}")
            
    return lessons_str
