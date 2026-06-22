import os
import time
import datetime
import traceback
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from pydantic import ValidationError

from src.agents.core import ContentGenerator, Critic, Editor, Librarian, FactChecker, InternalLibrarian, CurriculumJudgeEval, CourseQualityJudgeEval, Archivist
from src.utils.logger import log_event, update_status, update_telemetry
from src.utils.learning_engine import record_lesson
from src.models.schemas import CourseInput, TelemetryData, EvalResult

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STOP_FLAG = PROJECT_ROOT / "data" / "stop.flag"

def _check_stop(telemetry: Dict[str, Any], session_dir: Path) -> None:
    """Raise SystemExit if data/stop.flag exists. Stops token spend immediately."""
    if STOP_FLAG.exists():
        log_event("System", "Stop flag detected. Shutting down cleanly.", session_dir=str(session_dir))
        update_status("Stopped by user.", session_dir=str(session_dir))
        telemetry["status"] = "Stopped"
        telemetry["current_agent"] = "None"
        update_telemetry(telemetry, session_dir=str(session_dir))
        raise SystemExit(0)

def normalize_draft(draft: str, sub_title: str, required_headings: List[str]) -> str:
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
            # But do not strip the required major headings
            clean_reqs = [req.replace("### ", "").strip().lower() for req in required_headings]
            if not any(header in stripped.lower() for header in clean_reqs):
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

def update_live_preview(session_dir: Optional[Path], master_file: Path, sub_title: Optional[str] = None, draft: Optional[str] = None, status: Optional[str] = None) -> None:
    if not session_dir:
        return
    live_preview_file = session_dir / "live_preview.md"
    try:
        content = ""
        if master_file.exists():
            content = master_file.read_text(encoding="utf-8")
        
        if draft and sub_title:
            status_suffix = f" [{status}]" if status else " [Drafting]"
            content = content.rstrip()
            draft_clean = draft.strip()
            content += f"\n\n## Submodule: {sub_title}{status_suffix}\n\n{draft_clean}\n"
            
        live_preview_file.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"Error updating live preview: {e}")

def validate_draft(draft: str, required_headings: List[str]) -> List[str]:
    errors = []
    
    # Ignore conversational prefixes by finding the first required heading,
    # but only if there are no headings in the prefix before it.
    if required_headings and required_headings[0] in draft:
        prefix = draft[:draft.index(required_headings[0])]
        prefix_lines = [line.strip() for line in prefix.split('\n')]
        has_headings_in_prefix = any(line.startswith('#') for line in prefix_lines)
        if not has_headings_in_prefix:
            draft = draft[draft.index(required_headings[0]):]
        
    lines = [line.strip() for line in draft.split('\n')]
    
    # Check for presence of any # or ## headings
    for idx, line in enumerate(lines):
        if line.startswith('# ') or line.startswith('## '):
            errors.append(f"Line {idx+1}: Found illegal header level '{line}'. Only level 3 (###) and lower headers are allowed.")
            
    # Extract all level 3 headings
    headings = [line for line in lines if line.startswith('### ')]
    
    # Check for missing required headings
    for req in required_headings:
        if req not in headings:
            errors.append(f"Missing required major heading: '{req}'")
            
    # Check for duplicate required headings
    for req in required_headings:
        if headings.count(req) > 1:
            errors.append(f"Duplicate required heading: '{req}' appears multiple times.")
            
    # Check that first non-empty line starts with the first required heading
    non_empty_lines = [l for l in lines if l]
    if non_empty_lines and required_headings and not non_empty_lines[0].startswith(required_headings[0]):
        errors.append(f"First line of draft must be exactly '{required_headings[0]}'.")
        
    # Check order of required headings:
    indices = []
    for req in required_headings:
        try:
            indices.append(headings.index(req))
        except ValueError:
            pass
            
    if len(indices) == len(required_headings):
        if indices != sorted(indices):
            req_str = ", ".join([r.replace("### ", "") for r in required_headings])
            errors.append(f"Required headings are in the wrong order. Must be: {req_str}.")
            
    return errors

def sanitize_headings(draft: str, sub_title: str, required_headings: List[str]) -> str:
    # If the draft has a conversational prefix (e.g. from the Editor debate), strip it out.
    if required_headings:
        first_heading = required_headings[0]
        if first_heading in draft:
            draft = draft[draft.index(first_heading):]
            
    return normalize_draft(draft, sub_title, required_headings)

def main() -> None:
    # --- API KEY CHECK ---
    if not os.environ.get("GEMINI_API_KEY"):
        print("CRITICAL ERROR: GEMINI_API_KEY not found in environment. Please check your .env file.")
        return

    input_path = PROJECT_ROOT / 'data' / 'input' / 'course_input.json'
    output_dir = PROJECT_ROOT / 'data' / 'output'
    
    if not input_path.exists():
        print(f"ERROR: Input file not found at {input_path}")
        return

    try:
        data = json.loads(input_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: course_input.json is invalid JSON: {e}")
        return

    # --- SCHEMA PRE-VALIDATION WITH PYDANTIC ---
    try:
        course = CourseInput.model_validate(data)
    except ValidationError as e:
        print(f"CRITICAL ERROR: Course Input Schema Validation Failed:\n{e}")
        return

    # --- VERSIONING: Create a unique timestamped workspace ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = output_dir / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"Initializing new session in: {session_dir}")
    # ---------------------------------------------------------

    safe_course_name = "".join([c if c.isalnum() else "_" for c in course.course_name])
    master_file = session_dir / f"{safe_course_name}.md"
    
    # Initialize Agents
    generator = ContentGenerator("Content Generator", theme=course.prompt_theme)
    critic = Critic("Critic", theme=course.prompt_theme)
    editor = Editor("Editor", theme=course.prompt_theme)
    librarian = Librarian("Librarian", theme=course.prompt_theme)
    internal_librarian = InternalLibrarian("Internal Librarian", theme=course.prompt_theme)
    fact_checker = FactChecker("Fact-Checker", theme=course.prompt_theme)
    archivist = Archivist("Archivist", theme=course.prompt_theme)

    # For telemetry tracking
    telemetry = TelemetryData(
        status="Initializing",
        current_agent="System",
        progress_percent=0,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        model_name=generator.model_id,
        current_module="",
        current_submodule="",
        last_error_type="None",
        last_error_details="",
        active_iterations=0,
        passed_1st_iteration=0,
        passed_2nd_iteration=0,
        passed_3rd_iteration=0,
        failed_max_iterations=0,
        run_history=[]
    ).model_dump()

    # --- PRE-GENERATION EVAL: Curriculum Path Judge ---
    if os.environ.get("RUN_EVALS", "").lower() == "true":
        update_status("Running Curriculum Path Eval...", session_dir=str(session_dir))
        log_event("Evals", "Running Curriculum Path Eval...", session_dir=str(session_dir))
        curriculum_judge = CurriculumJudgeEval(theme=course.prompt_theme)
        try:
            eval_result_json = curriculum_judge.evaluate(
                course_name=course.course_name, 
                topic=course.topic, 
                duration_weeks=course.duration_weeks,
                outline=json.dumps([m.model_dump() for m in course.modules], indent=2)
            )
            eval_result = EvalResult.model_validate_json(eval_result_json)
            if not eval_result.passed:
                log_event("Evals", f"EVAL FAILED: Curriculum Path Judge\nRaw Output:\n{eval_result_json}", session_dir=str(session_dir))
                update_status("Pipeline halted due to Curriculum Eval Failure.", session_dir=str(session_dir))
                telemetry["status"] = "Stopped"
                telemetry["last_error_type"] = "Curriculum Eval Failed"
                update_telemetry(telemetry, session_dir=str(session_dir))
                return
            else:
                log_event("Evals", f"EVAL PASSED: Curriculum Path Judge\nRaw Output:\n{eval_result_json}", session_dir=str(session_dir))
        except Exception as e:
            log_event("Error", f"Curriculum Eval encountered an error, continuing pipeline... {e}", session_dir=str(session_dir))

    # 1. Start Book
    with open(master_file, 'w', encoding='utf-8') as f:
        f.write(f"# {course.course_name}\n\n")
        f.write(f"**Topic:** {course.topic}\n\n")
        f.write("# Table of Contents\n\n")
        for i, mod in enumerate(course.modules):
            title = mod.title.strip()
            if title.lower().startswith("module"):
                f.write(f"{title}\n")
            else:
                f.write(f"{i+1}. {title}\n")
            for sub in mod.submodules:
                sub_title = sub.title
                f.write(f"   - {sub_title}\n")
        f.write("\n---\n\n")
    
    update_live_preview(session_dir, master_file)
    log_event("System", "Starting generation pipeline (Class-Based Agents + Fact-Checking + Self-Learning)...")
    telemetry["status"] = "Running"
    update_telemetry(telemetry)

    total_submodules = sum(len(mod.submodules) for mod in course.modules)
    submodules_completed = 0
    running_summary = ""

    # 2. Module & Submodule Generation Loop
    # Extract course variables from course Pydantic model
    course_name = course.course_name
    course_topic = course.topic
    duration_weeks = course.duration_weeks

    # Dynamically build curriculum_structure representing module/submodule hierarchy
    curriculum_structure_lines = []
    for m_idx, m in enumerate(course.modules):
        m_title = m.title.strip()
        if m_title.lower().startswith("module"):
            curriculum_structure_lines.append(m_title)
        else:
            curriculum_structure_lines.append(f"Module {m_idx+1}: {m_title}")
        for s in m.submodules:
            curriculum_structure_lines.append(f"  - {s.title}")
    curriculum_structure = "\n".join(curriculum_structure_lines)

    try:
        for i, mod in enumerate(course.modules):
            _check_stop(telemetry, session_dir)  # Check before each module
            module_context = mod.module_context
            title = mod.title.strip()
            with open(master_file, 'a', encoding='utf-8') as f:
                if title.lower().startswith("module"):
                    f.write(f"\n# {title}\n\n")
                else:
                    f.write(f"\n# Module {i+1}: {title}\n\n")
            
            telemetry["current_module"] = mod.title
            
            for sub in mod.submodules:
                _check_stop(telemetry, session_dir)  # Check before EVERY submodule
                sub_title = sub.title
                content_context = sub.content_context
                
                update_status(f"Preparing {sub_title}...", session_dir=str(session_dir))
                time.sleep(2) 

                
                update_status(f"Generator Agent: Drafting '{sub_title}'", session_dir=str(session_dir))
                log_event("Generator", f"Drafting submodule: {sub_title}", session_dir=str(session_dir))
                telemetry["current_agent"] = "Generator"
                telemetry["current_submodule"] = sub_title
                telemetry["last_error_type"] = "None"
                telemetry["last_error_details"] = ""
                update_telemetry(telemetry, session_dir=str(session_dir))
                
                try:
                    # Pass content_context and running_summary along with course metadata
                    draft = generator.generate(
                        module_title=mod.title,
                        sub_title=sub_title,
                        content_context=content_context,
                        running_summary=running_summary,
                        course_info=course,
                        module_context=module_context
                    )
                    req_headings = generator.required_headings
                    draft = normalize_draft(draft, sub_title, req_headings)
                    update_live_preview(session_dir, master_file, sub_title, draft, "Drafting")
                    telemetry["input_tokens"] += generator.input_tokens
                    telemetry["output_tokens"] += generator.output_tokens
                    telemetry["total_tokens"] += generator.total_tokens
                except Exception as e:
                    error_msg = f"Drafting failed: {str(e)}"
                    log_event("Error", error_msg, session_dir=str(session_dir))
                    update_status(f"Error: {e}. Retrying...", session_dir=str(session_dir))
                    time.sleep(10)
                    continue
                
                # --- THE REFLECTIVE LOOP ---
                approved = False
                iterations = 0
                max_iterations = 3
                
                critic_chat = critic.start_chat_session()
                editor_chat = editor.start_chat_session()
                
                while not approved and iterations < max_iterations:
                    iterations += 1
                    telemetry["active_iterations"] = iterations
                    
                    # 1. DETERMINISTIC STRUCTURAL VALIDATION GATE
                    validation_errors = validate_draft(draft, req_headings)
                    if validation_errors:
                        validation_critique = "The draft failed structural validation:\n" + "\n".join([f"- {err}" for err in validation_errors])
                        log_event("Critic", f"Structural validation failed: {len(validation_errors)} errors.", session_dir=str(session_dir))
                        
                        update_status(f"Editor Agent: Repairing Structure of '{sub_title}'", session_dir=str(session_dir))
                        log_event("Editor", f"Repairing structure of {sub_title} based on validation errors.", session_dir=str(session_dir))
                        telemetry["current_agent"] = "Editor"
                        telemetry["last_error_type"] = "Structural Validation"
                        telemetry["last_error_details"] = "\n".join(validation_errors)
                        update_telemetry(telemetry, session_dir=str(session_dir))
                        
                        draft = editor.edit_chat(
                            chat_session=editor_chat,
                            draft=draft,
                            feedback=validation_critique,
                            sub_title=sub_title,
                            content_context=content_context,
                            course_info=course,
                            module_title=mod.title,
                            running_summary=running_summary,
                            module_context=module_context
                        )
                        draft = normalize_draft(draft, sub_title, req_headings)
                        update_live_preview(session_dir, master_file, sub_title, draft, "Repairing Structure")
                        telemetry["input_tokens"] += editor.input_tokens
                        telemetry["output_tokens"] += editor.output_tokens
                        telemetry["total_tokens"] += editor.total_tokens
                        
                        log_event("LearningEngine", f"Recording lesson for {sub_title}: Structural Error found.", session_dir=str(session_dir))
                        record_lesson(mod.title, sub_title, validation_critique, draft)
                        continue
                    
                    update_status(f"Critic Agent: Reviewing '{sub_title}' (Attempt {iterations})", session_dir=str(session_dir))
                    log_event("Critic", f"Reviewing {sub_title} (Attempt {iterations})", session_dir=str(session_dir))
                    telemetry["current_agent"] = "Critic"
                    update_telemetry(telemetry, session_dir=str(session_dir))
                    update_live_preview(session_dir, master_file, sub_title, draft, f"Critic Review (Attempt {iterations})")
                    
                    try:
                        # 2. CRITIC
                        feedback = critic.critique_chat(
                            chat_session=critic_chat,
                            draft=draft,
                            content_context=content_context,
                            course_info=course,
                            module_title=mod.title,
                            sub_title=sub_title,
                            running_summary=running_summary,
                            module_context=module_context
                        )
                        telemetry["input_tokens"] += critic.input_tokens
                        telemetry["output_tokens"] += critic.output_tokens
                        telemetry["total_tokens"] += critic.total_tokens
                        
                        if "APPROVED" in feedback.upper():
                            # 3. FACT-CHECK
                            update_status(f"Fact-Checker: Auditing '{sub_title}'", session_dir=str(session_dir))
                            log_event("Fact-Checker", f"Auditing {sub_title}", session_dir=str(session_dir))
                            telemetry["current_agent"] = "Fact-Checker"
                            update_telemetry(telemetry, session_dir=str(session_dir))
                            update_live_preview(session_dir, master_file, sub_title, draft, "Fact-Check Auditing")

                            fact_feedback = fact_checker.check_facts(draft, content_context)
                            telemetry["input_tokens"] += fact_checker.input_tokens
                            telemetry["output_tokens"] += fact_checker.output_tokens
                            telemetry["total_tokens"] += fact_checker.total_tokens

                            if "APPROVED" in fact_feedback.upper():
                                # 4. INTERNAL LIBRARIAN
                                update_status(f"Internal Librarian: Checking Markdown of '{sub_title}'", session_dir=str(session_dir))
                                log_event("InternalLibrarian", f"Checking markdown of {sub_title}", session_dir=str(session_dir))
                                telemetry["current_agent"] = "Internal Librarian"
                                update_telemetry(telemetry, session_dir=str(session_dir))
                                update_live_preview(session_dir, master_file, sub_title, draft, "Markdown Checking")

                                lib_feedback = internal_librarian.audit_draft(
                                    content=draft,
                                    course_info=course,
                                    module_context=module_context
                                )
                                telemetry["input_tokens"] += internal_librarian.input_tokens
                                telemetry["output_tokens"] += internal_librarian.output_tokens
                                telemetry["total_tokens"] += internal_librarian.total_tokens

                                if "APPROVED" in lib_feedback.upper():
                                    approved = True
                                    update_status(f"Approved: {sub_title}", session_dir=str(session_dir))
                                    log_event("InternalLibrarian", f"Approved: {sub_title}", session_dir=str(session_dir))
                                else:
                                    log_event("InternalLibrarian", f"Markdown issues found:\n{lib_feedback}", session_dir=str(session_dir))
                                    update_status(f"Editor Agent: Fixing Markdown in '{sub_title}'", session_dir=str(session_dir))
                                    log_event("Editor", f"Fixing {sub_title} based on Internal Librarian feedback.", session_dir=str(session_dir))
                                    telemetry["current_agent"] = "Editor"
                                    telemetry["last_error_type"] = "Internal Librarian Audit"
                                    telemetry["last_error_details"] = lib_feedback
                                    update_telemetry(telemetry, session_dir=str(session_dir))
                                    
                                    draft = editor.edit_chat(
                                        chat_session=editor_chat,
                                        draft=draft,
                                        feedback=lib_feedback,
                                        sub_title=sub_title,
                                        content_context=content_context,
                                        course_info=course,
                                        module_title=mod.title,
                                        running_summary=running_summary,
                                        module_context=module_context
                                    )
                                    draft = normalize_draft(draft, sub_title, req_headings)
                                    update_live_preview(session_dir, master_file, sub_title, draft, "Fixing Markdown")
                                    telemetry["input_tokens"] += editor.input_tokens
                                    telemetry["output_tokens"] += editor.output_tokens
                                    telemetry["total_tokens"] += editor.total_tokens
                                    
                                    log_event("LearningEngine", f"Recording lesson for {sub_title}: Markdown Error found.", session_dir=str(session_dir))
                                    record_lesson(mod.title, sub_title, lib_feedback, draft) 
                            else:
                                log_event("Fact-Checker", f"Issues found:\n{fact_feedback}", session_dir=str(session_dir))
                                update_status(f"Editor Agent: Fixing Fact-Errors in '{sub_title}'", session_dir=str(session_dir))
                                log_event("Editor", f"Fixing {sub_title} based on fact-checker feedback.", session_dir=str(session_dir))
                                telemetry["current_agent"] = "Editor"
                                telemetry["last_error_type"] = "Fact-Checker Audit"
                                telemetry["last_error_details"] = fact_feedback
                                update_telemetry(telemetry, session_dir=str(session_dir))
                                
                                draft = editor.edit_chat(
                                    chat_session=editor_chat,
                                    draft=draft,
                                    feedback=fact_feedback,
                                    sub_title=sub_title,
                                    content_context=content_context,
                                    course_info=course,
                                    module_title=mod.title,
                                    running_summary=running_summary,
                                    module_context=module_context
                                )
                                draft = normalize_draft(draft, sub_title, req_headings)
                                update_live_preview(session_dir, master_file, sub_title, draft, "Fixing Fact-Errors")
                                telemetry["input_tokens"] += editor.input_tokens
                                telemetry["output_tokens"] += editor.output_tokens
                                telemetry["total_tokens"] += editor.total_tokens
                                
                                log_event("LearningEngine", f"Recording lesson for {sub_title}: Fact Error found.", session_dir=str(session_dir))
                                record_lesson(mod.title, sub_title, fact_feedback, draft) 
                        else:
                            # 4. EDITOR
                            log_event("Critic", f"Issues found:\n{feedback}", session_dir=str(session_dir))
                            update_status(f"Editor Agent: Refining '{sub_title}'", session_dir=str(session_dir))
                            log_event("Editor", f"Refining {sub_title} based on feedback.", session_dir=str(session_dir))
                            telemetry["current_agent"] = "Editor"
                            telemetry["last_error_type"] = "Critic Review"
                            telemetry["last_error_details"] = feedback
                            update_telemetry(telemetry, session_dir=str(session_dir))
                            
                            draft = editor.edit_chat(
                                chat_session=editor_chat,
                                draft=draft,
                                feedback=feedback,
                                sub_title=sub_title,
                                content_context=content_context,
                                course_info=course,
                                module_title=mod.title,
                                running_summary=running_summary,
                                module_context=module_context
                            )
                            draft = normalize_draft(draft, sub_title, req_headings)
                            update_live_preview(session_dir, master_file, sub_title, draft, f"Refining Draft (Attempt {iterations})")
                            telemetry["input_tokens"] += editor.input_tokens
                            telemetry["output_tokens"] += editor.output_tokens
                            telemetry["total_tokens"] += editor.total_tokens
                            
                            log_event("LearningEngine", f"Recording lesson for {sub_title}: Structural/Tone Error found.", session_dir=str(session_dir))
                            record_lesson(mod.title, sub_title, feedback, draft) 
                    except Exception as e:
                        error_msg = f"Agent error: {str(e)}"
                        log_event("Error", error_msg, session_dir=str(session_dir))
                        update_status(f"Agent Error: {e}. Waiting...", session_dir=str(session_dir))
                        time.sleep(15)
                
                sanitized_draft = sanitize_headings(draft, sub_title, req_headings)
                with open(master_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n## Submodule: {sub_title}\n\n{sanitized_draft}\n\n")
                
                # --- TELEMETRY STATS TRACKING ---
                if approved:
                    if iterations == 1:
                        telemetry["passed_1st_iteration"] += 1
                    elif iterations == 2:
                        telemetry["passed_2nd_iteration"] += 1
                    elif iterations == 3:
                        telemetry["passed_3rd_iteration"] += 1
                else:
                    telemetry["failed_max_iterations"] += 1
                
                update_live_preview(session_dir, master_file)
                submodules_completed += 1
                telemetry["progress_percent"] = int((submodules_completed / total_submodules) * 100)
                telemetry["active_iterations"] = 0
                telemetry["last_error_type"] = "None"
                telemetry["last_error_details"] = ""
                update_telemetry(telemetry, session_dir=str(session_dir))
                update_telemetry(telemetry, session_dir=str(session_dir))
                
                # --- ITERATIVE COMPRESSION: THE ARCHIVIST ---
                update_status(f"Archivist: Compressing '{sub_title}'", session_dir=str(session_dir))
                log_event("Archivist", f"Summarizing {sub_title} for context injection.", session_dir=str(session_dir))
                try:
                    archivist_summary = archivist.compress_submodule(
                        content=sanitized_draft,
                        course_info=course,
                        module_title=mod.title,
                        sub_title=sub_title,
                        running_summary=running_summary
                    )
                    running_summary += f"\n- {sub_title}: {archivist_summary}"
                    
                    telemetry["input_tokens"] += archivist.input_tokens
                    telemetry["output_tokens"] += archivist.output_tokens
                    telemetry["total_tokens"] += archivist.total_tokens
                    update_telemetry(telemetry, session_dir=str(session_dir))
                except Exception as e:
                    log_event("Error", f"Archivist error: {e}. Skipping summary for this submodule.", session_dir=str(session_dir))
                
                time.sleep(5)
            
        # 5. GLOBAL LIBRARIAN PASS
        update_status("Global Librarian: Performing final structural audit of entire course...", session_dir=str(session_dir))
        log_event("Librarian", "Starting final structural audit of complete book.", session_dir=str(session_dir))
        telemetry["current_agent"] = "Librarian"
        update_telemetry(telemetry, session_dir=str(session_dir))
        
        try:
            if master_file.exists():
                full_book = master_file.read_text(encoding='utf-8')
                
                structure_feedback = librarian.audit_structure(
                    full_content=full_book,
                    curriculum_structure=curriculum_structure,
                    course_info=course
                )
                if "APPROVED" not in structure_feedback.upper():
                    error_msg = f"Structural issues found in final book:\n{structure_feedback}"
                    log_event("Librarian", error_msg, session_dir=str(session_dir))
                    
                    telemetry["last_error_type"] = "Global Librarian Audit"
                    telemetry["last_error_details"] = structure_feedback
                    update_telemetry(telemetry, session_dir=str(session_dir))
                    
                    log_event("LearningEngine", "Recording global lesson for structural issues.", session_dir=str(session_dir))
                    record_lesson("Global_Audit", "Structure", structure_feedback, "Adhere strictly to global structural requirements.")
                else:
                    log_event("Librarian", "Global Structure perfection confirmed.", session_dir=str(session_dir))
                    update_status("Librarian: Global Structure Approved.", session_dir=str(session_dir))
                
                # --- POST-GENERATION EVAL: Course Quality Judge ---
                if os.environ.get("RUN_EVALS", "").lower() == "true":
                    update_status("Running Course Quality Eval...", session_dir=str(session_dir))
                    log_event("Evals", "Running Course Quality Eval...", session_dir=str(session_dir))
                    quality_judge = CourseQualityJudgeEval(theme=course.prompt_theme)
                    try:
                        eval_result_json = quality_judge.evaluate(full_book)
                        eval_result = EvalResult.model_validate_json(eval_result_json)
                        log_event("CourseQualityEval", f"Raw Output:\n{eval_result_json}", session_dir=str(session_dir))
                        if not eval_result.passed:
                            update_status(f"Eval Failed: Course Quality (Score: {eval_result.score}/100)", session_dir=str(session_dir))
                            log_event("LearningEngine", "Recording global lesson for course quality failure.", session_dir=str(session_dir))
                            record_lesson("Global_Eval", "Course_Quality", eval_result.feedback, "Ensure academic depth, completeness, and rigor.")
                        else:
                            update_status(f"Eval Passed: Course Quality (Score: {eval_result.score}/100)", session_dir=str(session_dir))
                    except Exception as e:
                        log_event("Evals", f"Course Quality Eval error: {e}", session_dir=str(session_dir))
            else:
                log_event("Error", "Librarian failed: Master file was not found.", session_dir=str(session_dir))
        except Exception as e:
            error_msg = f"Librarian/Eval error: {str(e)}"
            log_event("Error", error_msg, session_dir=str(session_dir))
            update_status(f"Librarian/Eval Error: {e}", session_dir=str(session_dir))

        update_status("Generation Complete! Book Created.", session_dir=str(session_dir))
        log_event("System", "Course generation pipeline finished successfully.", session_dir=str(session_dir))
        telemetry["status"] = "Completed"
        update_telemetry(telemetry, session_dir=str(session_dir))
        
    except Exception as e:
        error_details = traceback.format_exc()
        log_event("CRITICAL ERROR", f"{str(e)}\n\n{error_details}", session_dir=str(session_dir))
        print(f"CRITICAL ERROR: {e}")
        print(error_details)
        
        update_status(f"CRITICAL ERROR: {e}", session_dir=str(session_dir))
        telemetry["status"] = "CRASHED"
        telemetry["last_error_type"] = "CRITICAL ERROR"
        telemetry["last_error_details"] = error_details
        update_telemetry(telemetry, session_dir=str(session_dir))
        raise e

if __name__ == "__main__":
    main()
