import os
import time
import datetime
import traceback
import json
from dotenv import load_dotenv
from src.agents.core import ContentGenerator, Critic, Editor, Librarian, FactChecker
from src.utils.logger import log_event, update_status, update_telemetry
from src.utils.learning_engine import record_lesson

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STOP_FLAG = os.path.join(PROJECT_ROOT, "data", "stop.flag")

def _check_stop(telemetry, session_dir):
    """Raise SystemExit if data/stop.flag exists. Stops token spend immediately."""
    if os.path.exists(STOP_FLAG):
        log_event("System", "Stop flag detected. Shutting down cleanly.", session_dir=session_dir)
        update_status("Stopped by user.", session_dir=session_dir)
        telemetry["status"] = "Stopped"
        telemetry["current_agent"] = "None"
        update_telemetry(telemetry, session_dir=session_dir)
        raise SystemExit(0)

def normalize_draft(draft, sub_title):
    import re
    # Normalize line endings and split
    lines = draft.replace('\r\n', '\n').split('\n')
    cleaned_lines = []
    
    # Clean sub_title by removing numbering like '1.1 ' at the beginning
    clean_title = re.sub(r'^[\d\.]+\s+', '', sub_title).strip().lower()
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines at the very beginning of the draft
        if not cleaned_lines and not stripped:
            continue
            
        # Skip module/submodule headings
        if stripped.lower().startswith('# module') or stripped.lower().startswith('## submodule'):
            continue
            
        # Skip any # or ## or ### headers containing the submodule title
        if (stripped.startswith('#') or stripped.startswith('##') or stripped.startswith('###')) and clean_title in stripped.lower():
            # But do not strip the required major headings like "Practical Application"
            if not any(header.lower() in stripped.lower() for header in [
                "introduction", "core concepts", "practical application", "summary and key takeaways"
            ]):
                continue
                
        cleaned_lines.append(line)
        
    normalized = '\n'.join(cleaned_lines).strip()
    
    # Remove duplicate adjacent lines if they are headings
    lines = normalized.split('\n')
    deduped_lines = []
    for line in lines:
        if deduped_lines and line.strip().startswith('###') and line.strip() == deduped_lines[-1].strip():
            continue
        deduped_lines.append(line)
        
    normalized = '\n'.join(deduped_lines).strip()
    
    # Normalize blank lines (maximum 2 consecutive blank lines)
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    
    return normalized

def update_live_preview(session_dir, master_file, sub_title=None, draft=None, status=None):
    if not session_dir:
        return
    live_preview_file = os.path.join(session_dir, "live_preview.md")
    try:
        content = ""
        if os.path.exists(master_file):
            with open(master_file, "r", encoding="utf-8") as f:
                content = f.read()
        
        if draft and sub_title:
            status_suffix = f" [{status}]" if status else " [Drafting]"
            content = content.rstrip()
            draft_clean = draft.strip()
            content += f"\n\n## Submodule: {sub_title}{status_suffix}\n\n{draft_clean}\n"
            
        with open(live_preview_file, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Error updating live preview: {e}")

def validate_draft(draft):
    errors = []
    lines = [line.strip() for line in draft.split('\n')]
    
    # Check for presence of any # or ## headings
    for idx, line in enumerate(lines):
        if line.startswith('# ') or line.startswith('## '):
            errors.append(f"Line {idx+1}: Found illegal header level '{line}'. Only level 3 (###) and lower headers are allowed.")
            
    # Extract all level 3 headings
    headings = [line for line in lines if line.startswith('### ')]
    
    required_headings = [
        "### Introduction",
        "### Core Concepts",
        "### Practical Application",
        "### Summary and Key Takeaways",
    ]
    
    # Check for missing required headings
    for req in required_headings:
        if req not in headings:
            errors.append(f"Missing required major heading: '{req}'")
            
    # Check for duplicate required headings
    for req in required_headings:
        if headings.count(req) > 1:
            errors.append(f"Duplicate required heading: '{req}' appears multiple times.")
            
    # Check that first non-empty line starts with ### Introduction
    non_empty_lines = [l for l in lines if l]
    if non_empty_lines and not non_empty_lines[0].startswith("### Introduction"):
        errors.append("First line of draft must be exactly '### Introduction'.")
        
    # Check order of required headings:
    indices = []
    for req in required_headings:
        try:
            indices.append(headings.index(req))
        except ValueError:
            pass
            
    if len(indices) == len(required_headings):
        if indices != sorted(indices):
            errors.append("Required headings are in the wrong order. Must be: Introduction, Core Concepts, Practical Application, Summary and Key Takeaways.")
            
    return errors

def sanitize_headings(draft, sub_title):
    return normalize_draft(draft, sub_title)

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

    # --- SCHEMA PRE-VALIDATION ---
    # Missing content_context must prevent lesson generation
    for mod in data.get('modules', []):
        for sub in mod.get('submodules', []):
            if isinstance(sub, str):
                raise ValueError(f"Submodule '{sub}' is a flat string. Missing required 'content_context'.")
            if not isinstance(sub, dict) or 'content_context' not in sub:
                raise ValueError(f"Submodule missing required 'content_context': {sub}")
            if not sub.get('title'):
                raise ValueError(f"Submodule missing required 'title': {sub}")

    # --- VERSIONING: Create a unique timestamped workspace ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(output_dir, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    print(f"Initializing new session in: {session_dir}")
    # ---------------------------------------------------------

    safe_course_name = "".join([c if c.isalnum() else "_" for c in data['course_name']])
    master_file = os.path.join(session_dir, f"{safe_course_name}.md")
    
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
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "model_name": generator.model_id,
        "current_module": "",
        "current_submodule": "",
        "active_iterations": 0,
        "last_error_type": "None",
        "last_error_details": ""
    }

    # 1. Start Book
    with open(master_file, 'w', encoding='utf-8') as f:
        f.write(f"# {data['course_name']}\n\n")
        f.write(f"**Topic:** {data['topic']}\n\n")
        f.write("# Table of Contents\n\n")
        for i, mod in enumerate(data['modules']):
            title = mod['title'].strip()
            if title.lower().startswith("module"):
                f.write(f"{title}\n")
            else:
                f.write(f"{i+1}. {title}\n")
            for sub in mod.get('submodules', []):
                sub_title = sub.get('title', 'Untitled')
                f.write(f"   - {sub_title}\n")
        f.write("\n---\n\n")
    
    update_live_preview(session_dir, master_file)
    log_event("System", "Starting generation pipeline (Class-Based Agents + Fact-Checking + Self-Learning)...")
    telemetry["status"] = "Running"
    update_telemetry(telemetry)

    total_submodules = sum(len(mod.get('submodules', [])) for mod in data['modules'])
    submodules_completed = 0

    # 2. Module & Submodule Generation Loop
    try:
        for i, mod in enumerate(data['modules']):
            _check_stop(telemetry, session_dir)  # Check before each module
            title = mod['title'].strip()
            with open(master_file, 'a', encoding='utf-8') as f:
                if title.lower().startswith("module"):
                    f.write(f"\n# {title}\n\n")
                else:
                    f.write(f"\n# Module {i+1}: {title}\n\n")
            
            telemetry["current_module"] = mod['title']
            
            for sub in mod.get('submodules', []):
                _check_stop(telemetry, session_dir)  # Check before EVERY submodule
                sub_title = sub['title']
                content_context = sub['content_context']
                
                update_status(f"Preparing {sub_title}...", session_dir=session_dir)
                time.sleep(2) 

                
                update_status(f"Generator Agent: Drafting '{sub_title}'", session_dir=session_dir)
                log_event("Generator", f"Drafting submodule: {sub_title}", session_dir=session_dir)
                telemetry["current_agent"] = "Generator"
                telemetry["current_submodule"] = sub_title
                telemetry["last_error_type"] = "None"
                telemetry["last_error_details"] = ""
                update_telemetry(telemetry, session_dir=session_dir)
                
                try:
                    # Pass content_context
                    draft = generator.generate(mod['title'], sub_title, content_context)
                    draft = normalize_draft(draft, sub_title)
                    update_live_preview(session_dir, master_file, sub_title, draft, "Drafting")
                    telemetry["input_tokens"] += generator.input_tokens
                    telemetry["output_tokens"] += generator.output_tokens
                    telemetry["total_tokens"] += generator.total_tokens
                except Exception as e:
                    error_msg = f"Drafting failed: {str(e)}"
                    log_event("Error", error_msg, session_dir=session_dir)
                    update_status(f"Error: {e}. Retrying...", session_dir=session_dir)
                    time.sleep(10)
                    continue
                
                # --- THE REFLECTIVE LOOP ---
                approved = False
                iterations = 0
                max_iterations = 3
                
                while not approved and iterations < max_iterations:
                    iterations += 1
                    telemetry["active_iterations"] = iterations
                    
                    # 1. DETERMINISTIC STRUCTURAL VALIDATION GATE
                    validation_errors = validate_draft(draft)
                    if validation_errors:
                        validation_critique = "The draft failed structural validation:\n" + "\n".join([f"- {err}" for err in validation_errors])
                        log_event("Critic", f"Structural validation failed: {len(validation_errors)} errors.", session_dir=session_dir)
                        
                        update_status(f"Editor Agent: Repairing Structure of '{sub_title}'", session_dir=session_dir)
                        log_event("Editor", f"Repairing structure of {sub_title} based on validation errors.", session_dir=session_dir)
                        telemetry["current_agent"] = "Editor"
                        telemetry["last_error_type"] = "Structural Validation"
                        telemetry["last_error_details"] = "\n".join(validation_errors)
                        update_telemetry(telemetry, session_dir=session_dir)
                        
                        draft = editor.edit(draft, validation_critique, sub_title, content_context)
                        draft = normalize_draft(draft, sub_title)
                        update_live_preview(session_dir, master_file, sub_title, draft, "Repairing Structure")
                        telemetry["input_tokens"] += editor.input_tokens
                        telemetry["output_tokens"] += editor.output_tokens
                        telemetry["total_tokens"] += editor.total_tokens
                        
                        log_event("LearningEngine", f"Recording lesson for {sub_title}: Structural Error found.", session_dir=session_dir)
                        record_lesson(mod['title'], sub_title, validation_critique, draft)
                        continue
                    
                    update_status(f"Critic Agent: Reviewing '{sub_title}' (Attempt {iterations})", session_dir=session_dir)
                    log_event("Critic", f"Reviewing {sub_title} (Attempt {iterations})", session_dir=session_dir)
                    telemetry["current_agent"] = "Critic"
                    update_telemetry(telemetry, session_dir=session_dir)
                    update_live_preview(session_dir, master_file, sub_title, draft, f"Critic Review (Attempt {iterations})")
                    
                    try:
                        # 2. CRITIC
                        feedback = critic.critique(draft, content_context)
                        telemetry["input_tokens"] += critic.input_tokens
                        telemetry["output_tokens"] += critic.output_tokens
                        telemetry["total_tokens"] += critic.total_tokens
                        
                        if "APPROVED" in feedback.upper():
                            # 3. FACT-CHECK
                            update_status(f"Fact-Checker: Auditing '{sub_title}'", session_dir=session_dir)
                            log_event("Fact-Checker", f"Auditing {sub_title}", session_dir=session_dir)
                            telemetry["current_agent"] = "Fact-Checker"
                            update_telemetry(telemetry, session_dir=session_dir)
                            update_live_preview(session_dir, master_file, sub_title, draft, "Fact-Check Auditing")

                            fact_feedback = fact_checker.check_facts(draft, content_context)
                            telemetry["input_tokens"] += fact_checker.input_tokens
                            telemetry["output_tokens"] += fact_checker.output_tokens
                            telemetry["total_tokens"] += fact_checker.total_tokens

                            if "APPROVED" in fact_feedback.upper():
                                approved = True
                                update_status(f"Approved: {sub_title}", session_dir=session_dir)
                                log_event("Critic", f"Approved: {sub_title}", session_dir=session_dir)
                            else:
                                update_status(f"Editor Agent: Fixing Fact-Errors in '{sub_title}'", session_dir=session_dir)
                                log_event("Editor", f"Fixing {sub_title} based on fact-checker feedback.", session_dir=session_dir)
                                telemetry["current_agent"] = "Editor"
                                telemetry["last_error_type"] = "Fact-Checker Audit"
                                telemetry["last_error_details"] = fact_feedback
                                update_telemetry(telemetry, session_dir=session_dir)
                                
                                draft = editor.edit(draft, fact_feedback, sub_title, content_context)
                                draft = normalize_draft(draft, sub_title)
                                update_live_preview(session_dir, master_file, sub_title, draft, "Fixing Fact-Errors")
                                telemetry["input_tokens"] += editor.input_tokens
                                telemetry["output_tokens"] += editor.output_tokens
                                telemetry["total_tokens"] += editor.total_tokens
                                
                                log_event("LearningEngine", f"Recording lesson for {sub_title}: Fact Error found.", session_dir=session_dir)
                                record_lesson(mod['title'], sub_title, fact_feedback, draft) 
                        else:
                            # 4. EDITOR
                            update_status(f"Editor Agent: Refining '{sub_title}'", session_dir=session_dir)
                            log_event("Editor", f"Refining {sub_title} based on feedback.", session_dir=session_dir)
                            telemetry["current_agent"] = "Editor"
                            telemetry["last_error_type"] = "Critic Review"
                            telemetry["last_error_details"] = feedback
                            update_telemetry(telemetry, session_dir=session_dir)
                            
                            draft = editor.edit(draft, feedback, sub_title, content_context)
                            draft = normalize_draft(draft, sub_title)
                            update_live_preview(session_dir, master_file, sub_title, draft, f"Refining Draft (Attempt {iterations})")
                            telemetry["input_tokens"] += editor.input_tokens
                            telemetry["output_tokens"] += editor.output_tokens
                            telemetry["total_tokens"] += editor.total_tokens
                            
                            log_event("LearningEngine", f"Recording lesson for {sub_title}: Structural/Tone Error found.", session_dir=session_dir)
                            record_lesson(mod['title'], sub_title, feedback, draft) 
                    except Exception as e:
                        error_msg = f"Agent error: {str(e)}"
                        log_event("Error", error_msg, session_dir=session_dir)
                        update_status(f"Agent Error: {e}. Waiting...", session_dir=session_dir)
                        time.sleep(15)
                
                sanitized_draft = sanitize_headings(draft, sub_title)
                with open(master_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n## Submodule: {sub_title}\n\n{sanitized_draft}\n\n")
                
                update_live_preview(session_dir, master_file)
                submodules_completed += 1
                telemetry["progress_percent"] = int((submodules_completed / total_submodules) * 100)
                telemetry["active_iterations"] = 0
                telemetry["last_error_type"] = "None"
                telemetry["last_error_details"] = ""
                update_telemetry(telemetry, session_dir=session_dir)
                time.sleep(5) 
            # 3. THE LIBRARIAN PASS
            update_status("Librarian Agent: Performing final structural audit...", session_dir=session_dir)
            log_event("Librarian", "Starting final structural audit of complete book.", session_dir=session_dir)
            telemetry["current_agent"] = "Librarian"
            update_telemetry(telemetry, session_dir=session_dir)
            
            try:
                if os.path.exists(master_file):
                    with open(master_file, 'r', encoding='utf-8') as f:
                        full_book = f.read()
                    
                    structure_feedback = librarian.audit_structure(full_book)
                    if "APPROVED" not in structure_feedback.upper():
                        error_msg = f"Structural issues found:\n{structure_feedback}"
                        log_event("Librarian", error_msg, session_dir=session_dir)
                        
                        telemetry["last_error_type"] = "Librarian Audit"
                        telemetry["last_error_details"] = structure_feedback
                        update_telemetry(telemetry, session_dir=session_dir)
                    else:
                        log_event("Librarian", "Structure perfection confirmed.", session_dir=session_dir)
                        update_status("Librarian: Structure Approved.", session_dir=session_dir)
                else:
                    log_event("Error", "Librarian failed: Master file was not found.", session_dir=session_dir)
            except Exception as e:
                error_msg = f"Librarian error: {str(e)}"
                log_event("Error", error_msg, session_dir=session_dir)
                update_status(f"Librarian Error: {e}", session_dir=session_dir)
            
        update_status("Generation Complete! Book Created.", session_dir=session_dir)
        log_event("System", "Course generation pipeline finished successfully.", session_dir=session_dir)
        telemetry["status"] = "Completed"
        update_telemetry(telemetry, session_dir=session_dir)
        
    except Exception as e:
        error_details = traceback.format_exc()
        log_event("CRITICAL ERROR", f"{str(e)}\n\n{error_details}", session_dir=session_dir)
        print(f"CRITICAL ERROR: {e}")
        print(error_details)
        
        update_status(f"CRITICAL ERROR: {e}", session_dir=session_dir)
        telemetry["status"] = "CRASHED"
        update_telemetry(telemetry, session_dir=session_dir)
        raise e

if __name__ == "__main__":
    main()
