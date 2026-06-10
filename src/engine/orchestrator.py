import json
import os
import time
import datetime
import traceback
from dotenv import load_dotenv
from src.agents.core import ContentGenerator, Critic, Editor, Librarian, FactChecker
from src.utils.logger import log_event, update_status
from src.utils.learning_engine import record_lesson

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def log_event(role, message):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    log_entry = f"[{ts}] **{role}**: {clean_message}\n"
    log_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, 'logs.txt'), 'a', encoding='utf-8') as f:
        f.write(log_entry)

def update_status(message):
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    status_dir = os.path.join(PROJECT_ROOT, 'data')
    os.makedirs(status_dir, exist_ok=True)
    with open(os.path.join(status_dir, 'status.txt'), 'w', encoding='utf-8') as f:
        f.write(clean_message)

def update_telemetry(data):
    """Writes real-time telemetry to a JSON file for the dashboard."""
    telemetry_file = os.path.join(PROJECT_ROOT, 'data', 'telemetry.json')
    data['timestamp'] = datetime.datetime.now().isoformat()
    try:
        with open(telemetry_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Telemetry Error: {e}")

def main():
    # --- API KEY CHECK ---
    if not os.environ.get("GEMINI_API_KEY"):
        print("CRITICAL ERROR: GEMINI_API_KEY not found in environment. Please check your .env file.")
        return

    input_path = os.path.join(PROJECT_ROOT, 'data', 'input', 'course_input.json')
    output_dir = os.path.join(PROJECT_ROOT, 'data', 'output')
    log_path = os.path.join(PROJECT_ROOT, 'data', 'logs.txt')
    telemetry_path = os.path.join(PROJECT_ROOT, 'data', 'telemetry.json')
    
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found at {input_path}")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)
    
    safe_course_name = "".join([c if c.isalnum() else "_" for c in data['course_name']])
    master_file = os.path.join(output_dir, f"{safe_course_name}.md")
    
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(log_path): os.remove(log_path)
    if os.path.exists(telemetry_path): os.remove(telemetry_path)

    # Initialize Agents
    generator = ContentGenerator("Content Generator")
    critic = Critic("Critic")
    editor = Editor("Editor")
    librarian = Librarian("Librarian")
    fact_checker = FactChecker("Fact-Checker")

    # For telemetry tracking
    telemetry = {
        "status": "Initializing",
        "current_agent": "System",
        "progress_percent": 0,
        "total_tokens": 0,
        "current_module": "",
        "current_submodule": "",
        "active_iterations": 0
    }

    # 1. Start Book
    with open(master_file, 'w', encoding='utf-8') as f:
        f.write(f"# {data['course_name']}\n\n")
        f.write(f"**Topic:** {data['topic']}\n\n")
        f.write("# Table of Contents\n\n")
        for i, mod in enumerate(data['modules']):
            f.write(f"{i+1}. {mod['title']}\n")
            for sub in mod.get('submodules', []):
                f.write(f"   - {sub}\n")
        f.write("\n---\n\n")
    
    log_event("System", "Starting generation pipeline (Class-Based Agents + Fact-Checking + Self-Learning)...")
    telemetry["status"] = "Running"
    update_telemetry(telemetry)

    total_submodules = sum(len(mod.get('submodules', [])) for mod in data['modules'])
    submodules_completed = 0

    # 2. Module & Submodule Generation Loop
    try:
        for i, mod in enumerate(data['modules']):
            with open(master_file, 'a', encoding='utf-8') as f:
                f.write(f"\n# Module {i+1}: {mod['title']}\n\n")
            
            telemetry["current_module"] = mod['title']
            
            for sub in mod.get('submodules', []):
                update_status(f"Preparing {sub}...")
                time.sleep(2) 
                
                update_status(f"Generator Agent: Drafting '{sub}'")
                log_event("Generator", f"Drafting submodule: {sub}")
                telemetry["current_agent"] = "Generator"
                update_telemetry(telemetry)
                
                try:
                    draft = generator.generate(mod['title'], sub)
                    telemetry["total_tokens"] += generator.tokens_used
                except Exception as e:
                    # IMPROVED ERROR LOGGING: Capture full error details
                    error_msg = f"Drafting failed: {str(e)}"
                    log_event("Error", error_msg)
                    update_status(f"Error: {e}. Retrying...")
                    time.sleep(10)
                    continue
                
                # --- THE REFLECTIVE LOOP ---
                approved = False
                iterations = 0
                max_iterations = 3
                
                while not approved and iterations < max_iterations:
                    iterations += 1
                    telemetry["active_iterations"] = iterations
                    update_status(f"Critic Agent: Reviewing '{sub}' (Attempt {iterations})")
                    log_event("Critic", f"Reviewing {sub} (Attempt {iterations})")
                    telemetry["current_agent"] = "Critic"
                    update_telemetry(telemetry)
                    
                    try:
                        # 1. CRITIC
                        feedback = critic.critique(draft)
                        telemetry["total_tokens"] += critic.tokens_used
                        
                        if "APPROVED" in feedback.upper():
                            # 2. FACT-CHECK (If critic approves, we still fact-check)
                            update_status(f"Fact-Checker: Auditing '{sub}'")
                            log_event("Fact-Checker", f"Auditing {sub}")
                            telemetry["current_agent"] = "Fact-Checker"
                            update_telemetry(telemetry)

                            fact_feedback = fact_checker.check_facts(draft)
                            telemetry["total_tokens"] += fact_checker.tokens_used

                            if "APPROVED" in fact_feedback.upper():
                                approved = True
                                update_status(f"Approved: {sub}")
                                log_event("Critic", f"Approved: {sub}")
                            else:
                                # If Fact-Checker finds issues, trigger an Editor pass
                                update_status(f"Editor Agent: Fixing Fact-Errors in '{sub}'")
                                log_event("Editor", f"Fixing {sub} based on fact-checker feedback.")
                                telemetry["current_agent"] = "Editor"
                                update_telemetry(telemetry)
                                
                                draft = editor.edit(draft, fact_feedback)
                                telemetry["total_tokens"] += editor.tokens_used
                                
                                # --- SELF-LEARNING: RECORD THE LESSON ---
                                log_event("LearningEngine", f"Recording lesson for {sub}: Fact Error found.")
                                record_lesson(mod['title'], sub, fact_feedback, draft)
                                
                                iterations += 1 
                        else:
                            # 3. EDITOR (If critic found issues)
                            update_status(f"Editor Agent: Refining '{sub}'")
                            log_event("Editor", f"Refining {sub} based on feedback.")
                            telemetry["current_agent"] = "Editor"
                            update_telemetry(telemetry)
                            
                            draft = editor.edit(draft, feedback)
                            telemetry["total_tokens"] += editor.tokens_used
                            
                            # --- SELF-LEARNING: RECORD THE LESSON ---
                            log_event("LearningEngine", f"Recording lesson for {sub}: Structural/Tone Error found.")
                            record_lesson(mod['title'], sub, feedback, draft)
                            
                            iterations += 1 
                    except Exception as e:
                        # IMPROVED ERROR LOGGING: Capture full error details
                        error_msg = f"Agent error: {str(e)}"
                        log_event("Error", error_msg)
                        update_status(f"Agent Error: {e}. Waiting...")
                        time.sleep(15)
                
                with open(master_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n## Submodule: {sub}\n\n{draft}\n\n")
                
                submodules_completed += 1
                telemetry["progress_percent"] = int((submodules_completed / total_submodules) * 100)
                telemetry["active_iterations"] = 0
                update_telemetry(telemetry)
                time.sleep(5) 
                
            # 3. THE LIBRARIAN PASS (Final Structural Audit)
            update_status("Librarian Agent: Performing final structural audit...")
            log_event("Librarian", "Starting final structural audit of complete book.")
            telemetry["current_agent"] = "Librarian"
            update_telemetry(telemetry)
            
            try:
                # Fix: Ensure full_book is loaded safely within the Librarian pass
                if os.path.exists(master_file):
                    with open(master_file, 'r', encoding='utf-8') as f:
                        full_book = f.read()
                    
                    structure_feedback = librarian.audit_structure(full_book)
                    if "APPROVED" not in structure_feedback.upper():
                        log_event("Librarian", "Structural issues found. Appending audit log.")
                        with open(master_file, 'a', encoding='utf-8') as f:
                            f.write(f"\n\n---\n\n### Structural Audit Log\n{structure_feedback}\n")
                    else:
                        log_event("Librarian", "Structure perfection confirmed.")
                        update_status("Librarian: Structure Approved.")
                else:
                    log_event("Error", "Librarian failed: Master file was not found.")
            except Exception as e:
                # IMPROVED ERROR LOGGING: Capture full error details
                error_msg = f"Librarian error: {str(e)}"
                log_event("Error", error_msg)
                update_status(f"Librarian Error: {e}")
            
        update_status("Generation Complete! Book Created.")
        log_event("System", "Course generation pipeline finished successfully.")
        telemetry["status"] = "Completed"
        update_telemetry(telemetry)

    except Exception as e:
        # LOG FULL TRACEBACK ON CRITICAL ERROR
        error_details = traceback.format_exc()
        log_event("CRITICAL ERROR", f"{str(e)}\n\n{error_details}")
        print(f"CRITICAL ERROR: {e}")
        print(error_details)
        
        update_status(f"CRITICAL ERROR: {e}")
        telemetry["status"] = "CRASHED"
        update_telemetry(telemetry)
        raise e

if __name__ == "__main__":
    main()
