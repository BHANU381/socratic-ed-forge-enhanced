import os
import sys
import json
import signal
import subprocess
import asyncio
import glob
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR      = PROJECT_ROOT / "data"
INPUT_DIR     = DATA_DIR / "input"
OUTPUT_DIR    = DATA_DIR / "output"
LOG_FILE      = DATA_DIR / "logs.txt"
TELEMETRY_FILE= DATA_DIR / "telemetry.json"
PID_FILE      = DATA_DIR / "runner.pid"
STOP_FLAG     = DATA_DIR / "stop.flag"   # Orchestrator polls this; exits if present
PROMPTS_DIR   = PROJECT_ROOT / "src" / "prompts"

# ── Helpers ───────────────────────────────────────────────────────────────────
def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else (default or {})
    except Exception:
        return default or {}

def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _get_pid() -> Optional[int]:
    try:
        return int(PID_FILE.read_text().strip()) if PID_FILE.exists() else None
    except (ValueError, OSError):
        return None

def _is_running(pid: int) -> bool:
    """Check if a PID is alive."""
    if not pid: return False
    if os.name == 'nt':
        try:
            output = subprocess.check_output(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return str(pid) in output
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

def _kill_process_tree(pid: int):
    """
    ROBUST STOP - Three redundant kill layers:
    Layer 1: taskkill /F /T kills entire Windows process tree (children too)
    Layer 2: Fallback SIGTERM then SIGKILL via os.kill
    Layer 3: Any exception is swallowed - we always clean up the PID file
    """
    # Layer 1: Windows taskkill - kills the process AND all its children
    try:
        subprocess.run(
            ['taskkill', '/F', '/T', '/PID', str(pid)],
            capture_output=True, timeout=10
        )
    except Exception:
        pass

    # Layer 2: POSIX fallback
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if _is_running(pid):
            os.kill(pid, signal.SIGKILL)
    except (OSError, AttributeError):
        pass

def _cleanup_after_stop():
    """Remove PID file and stop flag, update telemetry."""
    try: PID_FILE.unlink()
    except FileNotFoundError: pass
    try: STOP_FLAG.unlink()
    except FileNotFoundError: pass

def get_latest_book() -> Optional[Path]:
    session_dirs = sorted(OUTPUT_DIR.glob("session_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for sd in session_dirs:
        manifest_file = sd / "run_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                if m_data.get("run_type") == "test_run":
                    continue
            except Exception:
                pass
        live = sd / "live_preview.md"
        if live.exists():
            return live
        md_files = [f for f in sd.glob("*.md") if f.name != "live_preview.md"]
        if md_files:
            return max(md_files, key=lambda p: p.stat().st_mtime)
    return None

def get_log_tail(n: Optional[int] = None) -> list[str]:
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        return lines[-n:] if n is not None else lines
    except Exception:
        return []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On every server start: audit the PID file.
    If the saved PID is no longer alive, clean it up so the UI
    starts fresh and does NOT show a phantom 'running' state.
    This prevents stale token-burning processes from being invisible.
    """
    pid = _get_pid()
    if pid and not _is_running(pid):
        _cleanup_after_stop()
        tel = _read_json(TELEMETRY_FILE)
        tel["status"] = "Idle (previous run ended unexpectedly)"
        _write_json(TELEMETRY_FILE, tel)
    # Also remove any leftover stop.flag from a previous session
    try: STOP_FLAG.unlink()
    except FileNotFoundError: pass
    
    yield
    
    # Teardown: Terminate running pipeline process on server exit to prevent leaks
    pid = _get_pid()
    if pid and _is_running(pid):
        try: STOP_FLAG.write_text("STOP")
        except Exception: pass
        _kill_process_tree(pid)
        _cleanup_after_stop()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Socratic Ed-Forge API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.get("/api/status")
def get_status():
    pid = _get_pid()
    is_running = bool(pid and _is_running(pid))
    tel = _read_json(TELEMETRY_FILE)
    
    if tel.get("status") in ["Completed", "Stopped by user", "CRASHED", "Idle (previous run ended unexpectedly)"]:
        is_running = False
        
    return JSONResponse({"is_running": is_running, "pid": pid, "telemetry": tel})

@app.get("/api/logs")
def get_logs(n: Optional[int] = None):
    return JSONResponse({"lines": get_log_tail(n)})

@app.get("/api/preview")
def get_preview():
    book = get_latest_book()
    if not book:
        return JSONResponse({"content": None, "filename": None, "is_live": False})
    content = book.read_text(encoding="utf-8")
    return JSONResponse({
        "content": content,
        "filename": book.name,
        "is_live": book.name == "live_preview.md"
    })

@app.get("/api/prompt-themes")
def get_prompt_themes():
    from src.utils.prompt_loader import PROMPTS_DIR
    import os
    if not os.path.exists(PROMPTS_DIR):
        return JSONResponse({"themes": ["default"]})
        
    themes = [d for d in os.listdir(PROMPTS_DIR) if os.path.isdir(os.path.join(PROMPTS_DIR, d))]
    # Ensure 'default' is always present and first if it exists
    if "default" in themes:
        themes.remove("default")
        themes.insert(0, "default")
    elif not themes:
        themes = ["default"]
        
    return JSONResponse({"themes": themes})

@app.post("/api/start")
async def start_pipeline(
    file: UploadFile = File(...),
    rpm_limit: Optional[int] = Form(None),
    tpm_limit: Optional[int] = Form(None),
    prompt_theme: Optional[str] = Form(None),
    learner_level: Optional[str] = Form(None),
    code_example_style: Optional[str] = Form(None),
    explanation_depth: Optional[str] = Form(None),
    quality_profile: Optional[str] = Form(None),
    enable_google_search: Optional[bool] = Form(None),
    review_granularity: Optional[str] = Form(None),
    resume: Optional[bool] = Form(None)
):
    pid = _get_pid()
    if pid and _is_running(pid):
        raise HTTPException(status_code=409, detail="Pipeline already running.")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_bytes = await file.read()
    try:
        data = json.loads(file_bytes)  # Validate JSON
        if prompt_theme is not None:
            data["prompt_theme"] = prompt_theme
        if learner_level is not None:
            data["learner_level"] = learner_level
        if code_example_style is not None:
            data["code_example_style"] = code_example_style
        if explanation_depth is not None:
            data["explanation_depth"] = explanation_depth
        if quality_profile is not None:
            data["quality_profile"] = quality_profile
        if enable_google_search is not None:
            data["enable_google_search"] = enable_google_search
        if review_granularity is not None:
            data["review_granularity"] = review_granularity
            
        # Validate schema and normalize it to ensure the structure is correct
        from src.models.schemas import normalize_course_input
        normalize_course_input(data)
        
        # Rewrite the modified data to file_bytes to be saved
        file_bytes = json.dumps(data, indent=4).encode('utf-8')
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, (ValidationError, ValueError)):
            raise HTTPException(status_code=422, detail=f"Schema Validation Failed: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    config_path = INPUT_DIR / "course_input.json"
    
    # Non-blocking IO to write the file
    await asyncio.to_thread(config_path.write_bytes, file_bytes)

    # Clean up any leftover stop flag from previous run
    try: STOP_FLAG.unlink()
    except FileNotFoundError: pass

    # Reset telemetry
    init_tel = {
        "status": "Initializing",
        "progress_percent": 0,
        "current_agent": "System",
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model_name": "N/A",
        "current_module": "N/A",
        "current_submodule": "N/A",
        "last_error_type": "None",
        "last_error_details": ""
    }
    _write_json(TELEMETRY_FILE, init_tel)
    if LOG_FILE.exists(): LOG_FILE.unlink()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["RUN_TYPE"] = "resume_existing_run" if resume else "new_run"
    if rpm_limit is not None:
        env["RPM_LIMIT"] = str(rpm_limit)
    if tpm_limit is not None:
        env["TPM_LIMIT"] = str(tpm_limit)

    # Use the standard sys.executable. To ensure this works perfectly across all OSes
    # and environments (venv, poetry, global), the app should be launched via 
    # `python -m uvicorn` rather than the `uvicorn` wrapper binary.
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.engine.orchestrator"],
        cwd=str(PROJECT_ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # Windows: enables /T tree kill
    )

    # Write PID immediately
    PID_FILE.write_text(str(proc.pid))

    return JSONResponse({"status": "started", "pid": proc.pid})

@app.post("/api/stop")
def stop_pipeline():
    pid = _get_pid()

    # Layer 0: Write stop flag - orchestrator will exit cleanly at next iteration
    STOP_FLAG.write_text("STOP")

    if not pid:
        return JSONResponse({"status": "not_running", "detail": "No PID on record."})

    if not _is_running(pid):
        _cleanup_after_stop()
        return JSONResponse({"status": "already_stopped", "detail": "Process was not alive."})

    # Layers 1-3: Kill process tree
    _kill_process_tree(pid)

    # Final check
    still_alive = _is_running(pid) if pid else False
    _cleanup_after_stop()

    tel = _read_json(TELEMETRY_FILE)
    tel["status"] = "Stopped by user"
    tel["current_agent"] = "None"
    _write_json(TELEMETRY_FILE, tel)

    if LOG_FILE.exists():
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = time.strftime("%H:%M:%S")
            f.write(f"[{ts}] **System**: Generation stopped by user.\n")

    return JSONResponse({
        "status": "stopped" if not still_alive else "kill_attempted",
        "pid": pid
    })

@app.delete("/api/logs")
def clear_logs():
    try: LOG_FILE.unlink()
    except FileNotFoundError: pass
    try: TELEMETRY_FILE.unlink()
    except FileNotFoundError: pass
    return JSONResponse({"status": "cleared"})


from pydantic import BaseModel

class EditSessionPayload(BaseModel):
    session_id: str
    submodule_filename: str
    content: str

class ApprovePayload(BaseModel):
    session_id: str

class SelectionEditPayload(BaseModel):
    session_id: str
    selection_text: str
    instruction: str
    theme: str = "default"
    full_text: Optional[str] = None
    scope: str = "selection"

class SingleEditItem(BaseModel):
    original_text: str
    instruction: str

class BatchEditPayload(BaseModel):
    session_id: str
    theme: str = "default"
    full_text: str
    edits: list[SingleEditItem]

class ChatPayload(BaseModel):
    session_id: str
    message: str
    submodule_filename: str

def _get_containing_paragraph(full_text: str, selection: str) -> str:
    idx = full_text.find(selection)
    if idx == -1:
        return selection
    # Find start of paragraph (double newline backward)
    start = full_text.rfind('\n\n', 0, idx)
    if start == -1:
        start = 0
    else:
        start += 2 # skip the double newline
    # Find end of paragraph (double newline forward)
    end = full_text.find('\n\n', idx + len(selection))
    if end == -1:
        end = len(full_text)
    return full_text[start:end].strip()

def _get_section_rules(theme: str, heading: str) -> str:
    theme_path = PROMPTS_DIR / theme / "content_generator.md"
    if not theme_path.exists():
        theme_path = PROMPTS_DIR / "default" / "content_generator.md"
    if not theme_path.exists():
        return ""
        
    try:
        lines = theme_path.read_text(encoding="utf-8").split("\n")
    except Exception:
        return ""
        
    target = heading.strip().lower()
    norm_target = "".join(c for c in target if c.isalnum())
    
    rules = []
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            norm_line = "".join(c for c in stripped if c.isalnum()).lower()
            if norm_line == norm_target or norm_target in norm_line or norm_line in norm_target:
                found = True
                continue
            elif found:
                break
        if found:
            rules.append(line)
            
    return "\n".join(rules).strip()

def _find_crossed_headings(full_text: str, selection: str) -> list[str]:
    idx = full_text.find(selection)
    if idx == -1:
        return ["#### General"]
        
    start_idx = idx
    end_idx = idx + len(selection)
    
    preceding_heading = "#### General"
    lines_before = full_text[:start_idx].split("\n")
    for line in reversed(lines_before):
        line = line.strip()
        if line.startswith("###") or line.startswith("####"):
            preceding_heading = line
            break
            
    crossed = [preceding_heading]
    selection_area = full_text[start_idx:end_idx]
    for line in selection_area.split("\n"):
        line = line.strip()
        if line.startswith("###") or line.startswith("####"):
            if line not in crossed:
                crossed.append(line)
                
    return crossed

@app.post("/api/session/approve")
def approve_module(payload: ApprovePayload):
    if ".." in payload.session_id or "/" in payload.session_id or "\\" in payload.session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    session_dir = OUTPUT_DIR / payload.session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
        
    pause_file = session_dir / "module_pause.json"
    if pause_file.exists():
        try:
            with open(pause_file, "r+", encoding="utf-8") as f:
                data = json.load(f)
                data["status"] = "approved"
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse({"status": "approved"})

import re

def sanitize_html_to_markdown(text: str) -> str:
    if not text:
        return text
    # 1. Convert list items <li> to Markdown bullets *
    text = re.sub(r'<li>\s*', r'\n* ', text)
    text = re.sub(r'</li>', '', text)
    # 2. Convert strong tags to **
    text = re.sub(r'</?strong>', '**', text)
    # 3. Strip structural tags like <ul>, </ul>, <ol>, </ol>, <p>, </p>
    text = re.sub(r'</?(?:ul|ol|p)>', '', text)
    # 4. Collapse consecutive line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def validate_patch_scope(original: str, patched: str) -> bool:
    # 1. Heading structure matching
    orig_headings = [h.strip() for h in re.findall(r'^#+\s+.*$', original, re.M)]
    pat_headings = [h.strip() for h in re.findall(r'^#+\s+.*$', patched, re.M)]
    if orig_headings != pat_headings:
        return False
        
    # 2. Bullet point (*) and numbered list item count matching
    orig_bullets = len(re.findall(r'^\s*[\*\-]\s+', original, re.M))
    pat_bullets = len(re.findall(r'^\s*[\*\-]\s+', patched, re.M))
    orig_numbered = len(re.findall(r'^\s*\d+\.\s+', original, re.M))
    pat_numbered = len(re.findall(r'^\s*\d+\.\s+', patched, re.M))
    
    if orig_bullets != pat_bullets or orig_numbered != pat_numbered:
        return False
        
    # 3. Prevent structural wipeout (e.g. over-deletion of selections > 15 chars)
    if len(original) > 15 and len(patched) < (len(original) * 0.45):
        return False
        
    return True

def validate_patch_grounding(patched: str, context: str) -> bool:
    # Extract uppercase entities/acronyms of 3-6 chars (e.g. ICAM, ROI) from the context
    terms = set(re.findall(r'\b[A-Z]{3,6}\b', context))
    for t in terms:
        if t not in patched:
            return False
    return True

def run_patch_validation_loop(editor, draft: str, feedback: str, heading: str, grounding_context: str, original_text: str, max_retries: int = 3) -> str:
    current_feedback = feedback
    last_patched_str = ""
    
    for attempt in range(max_retries):
        patched = editor.edit_patch(
            draft=draft,
            feedback=current_feedback,
            heading=heading,
            course_topic="Custom editing",
            submodule_title="Custom lesson",
            grounding_context=grounding_context
        )
        
        if hasattr(patched, "replacement_markdown"):
            patched_str = patched.replacement_markdown
        elif hasattr(patched, "patched_content"):
            patched_str = patched.patched_content
        elif isinstance(patched, str):
            patched_str = patched
        else:
            patched_str = str(patched)
            
        patched_str = sanitize_html_to_markdown(patched_str)
        last_patched_str = patched_str
        
        # Run validations
        scope_ok = validate_patch_scope(original_text, patched_str)
        grounding_ok = validate_patch_grounding(patched_str, original_text)
        
        if scope_ok and grounding_ok:
            return patched_str
            
        # If invalid, refine feedback for next attempt
        failures = []
        if not scope_ok:
            failures.append("retaining the exact heading structures/markdown formatting")
        if not grounding_ok:
            missing_terms = [t for t in set(re.findall(r'\b[A-Z]{3,6}\b', original_text)) if t not in patched_str]
            failures.append(f"preserving key concepts: {', '.join(missing_terms)}")
            
        current_feedback = f"{feedback} (Note: Your previous attempt failed validation. Please revise it while strictly {', and '.join(failures)}.)"
        
    return last_patched_str if last_patched_str else draft
        
def run_batch_patch_validation(editor, edits: list[dict], grounding_context: str, max_retries: int = 3) -> list[str]:
    results = []
    for item in edits:
        original = item.get("original_text", "")
        instruction = item.get("instruction", "")
        # Run isolated validation loop for each selection independently
        patched_item = run_patch_validation_loop(
            editor=editor,
            draft=original,
            feedback=instruction,
            heading="Section Update",
            grounding_context=grounding_context,
            original_text=original,
            max_retries=max_retries
        )
        results.append(patched_item)
    return results

@app.post("/api/session/edit/selection")
def edit_selection(payload: SelectionEditPayload):
    if ".." in payload.session_id or "/" in payload.session_id or "\\" in payload.session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    from src.agents.core import PatchEditor
    try:
        editor = PatchEditor(theme=payload.theme)
        
        # Determine draft scope context
        draft_text = payload.selection_text
        if payload.scope == "paragraph" and payload.full_text:
            draft_text = _get_containing_paragraph(payload.full_text, payload.selection_text)
            
        # Dynamically compile heading and section rules context
        headings = _find_crossed_headings(payload.full_text or "", payload.selection_text)
        heading_title = " & ".join(headings)
        
        rules_list = []
        for h in headings:
            rules_list.append(f"Rules for {h}:\n{_get_section_rules(payload.theme, h)}")
        compound_rules = "\n\n".join(rules_list)
        
        grounding_context = payload.full_text or ""
        if compound_rules:
            grounding_context += f"\n\nTarget Prompt Template Directives:\n{compound_rules}"
            
        patched_str = run_patch_validation_loop(
            editor=editor,
            draft=draft_text,
            feedback=payload.instruction,
            heading=heading_title,
            grounding_context=grounding_context,
            original_text=payload.selection_text
        )
            
        # Accumulate token metrics in centralized session telemetry
        session_dir = OUTPUT_DIR / payload.session_id
        manifest_path = session_dir / "run_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                
                input_t = getattr(editor, "input_tokens", 0) or 0
                output_t = getattr(editor, "output_tokens", 0) or 0
                total_t = input_t + output_t
                
                manifest_data["total_tokens"] = manifest_data.get("total_tokens", 0) + total_t
                if "agent_tokens" not in manifest_data:
                    manifest_data["agent_tokens"] = {}
                manifest_data["agent_tokens"]["patch_editor"] = manifest_data["agent_tokens"].get("patch_editor", 0) + total_t
                
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, indent=4)
            except Exception:
                pass
                
        return JSONResponse({"patched_text": patched_str})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/edit/selection/batch")
def edit_selection_batch(payload: BatchEditPayload):
    if ".." in payload.session_id or "/" in payload.session_id or "\\" in payload.session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    from src.agents.core import PatchEditor
    try:
        editor = PatchEditor(theme=payload.theme)
        
        # Format the edits as dictionaries
        edits_dict = [{"original_text": e.original_text, "instruction": e.instruction} for e in payload.edits]
        
        # Run batch patch generation with validators
        patched_list = run_batch_patch_validation(
            editor=editor,
            edits=edits_dict,
            grounding_context=payload.full_text
        )
        
        # Accumulate token metrics in centralized session telemetry
        session_dir = OUTPUT_DIR / payload.session_id
        manifest_path = session_dir / "run_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                
                input_t = getattr(editor, "input_tokens", 0) or 0
                output_t = getattr(editor, "output_tokens", 0) or 0
                total_t = input_t + output_t
                
                manifest_data["total_tokens"] = manifest_data.get("total_tokens", 0) + total_t
                if "agent_tokens" not in manifest_data:
                    manifest_data["agent_tokens"] = {}
                manifest_data["agent_tokens"]["patch_editor"] = manifest_data["agent_tokens"].get("patch_editor", 0) + total_t
                
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, indent=4)
            except Exception:
                pass
                
        return JSONResponse({"patched_texts": patched_list})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/chat")
def chat_with_agent(payload: ChatPayload):
    if ".." in payload.session_id or "/" in payload.session_id or "\\" in payload.session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    from src.agents.core import AgentBase
    
    session_dir = OUTPUT_DIR / payload.session_id
    submodule_path = session_dir / payload.submodule_filename
    submodule_text = ""
    if submodule_path.exists():
        submodule_text = submodule_path.read_text(encoding="utf-8")
        
    prompt = f"User is reviewing the following submodule lesson:\n\n```markdown\n{submodule_text}\n```\n\nUser Question/Instruction: {payload.message}\n\nRespond as a helpful course editor agent with suggestions or revised markdown blocks."
    
    try:
        agent = AgentBase(role="Course Review Assistant")
        agent.system_instruction = "You are a helpful course editor assistant. Converse with the user, answer questions about the submodule text, or suggest improvements."
        response_text = agent._run_with_retry(prompt)
        return JSONResponse({"response": response_text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
def get_sessions():
    sessions = []
    if OUTPUT_DIR.exists():
        for p in OUTPUT_DIR.iterdir():
            if p.is_dir():
                manifest_path = p / "run_manifest.json"
                metadata = {}
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                    except Exception:
                        pass
                sessions.append({
                    "session_id": p.name,
                    "metadata": metadata
                })
    return JSONResponse({"sessions": sessions})

def _recompile_session_master(session_dir: Path):
    from src.engine.orchestrator import compile_master_file
    from src.models.schemas import normalize_course_input
    import re
    
    input_path = INPUT_DIR / "course_input.json"
    if not input_path.exists():
        return
        
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        course = normalize_course_input(data)
        safe_course_name = re.sub(r'[^a-zA-Z0-9_]', '_', course.course_title)
        master_file_path = session_dir / f"{safe_course_name}.md"
        compile_master_file(session_dir, master_file_path, course)
    except Exception:
        pass

@app.post("/api/sessions/edit")
def edit_session(payload: EditSessionPayload):
    if ".." in payload.session_id or "/" in payload.session_id or "\\" in payload.session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    if ".." in payload.submodule_filename or "/" in payload.submodule_filename or "\\" in payload.submodule_filename:
        raise HTTPException(status_code=400, detail="Invalid submodule_filename")
        
    session_dir = OUTPUT_DIR / payload.session_id
    if not session_dir.exists() or not session_dir.is_dir():
        raise HTTPException(status_code=404, detail="Session directory not found")
        
    file_path = session_dir / payload.submodule_filename
    try:
        file_path.write_text(payload.content, encoding="utf-8")
        _recompile_session_master(session_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")
        
    return JSONResponse({"status": "updated"})


@app.get("/api/sessions/{session_id}/preview")
def get_session_preview(session_id: str):
    if ".." in session_id or "/" in session_id or "\\" in session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    session_dir = OUTPUT_DIR / session_id
    if not session_dir.exists() or not session_dir.is_dir():
        raise HTTPException(status_code=404, detail="Session not found")
        
    for f in session_dir.glob("*.md"):
        if f.name != "live_preview.md" and f.name != "breakpoint.json":
            return JSONResponse({"content": f.read_text(encoding="utf-8"), "filename": f.name})
            
    return JSONResponse({"content": "", "filename": ""})


# ── SSE Stream ────────────────────────────────────────────────────────────────
@app.get("/api/stream")
async def stream(interval: float = 1.5):
    """
    Server-Sent Events stream. Client connects once;
    server pushes updates. No polling loop needed in the UI.
    """
    async def event_generator():
        last_valid_telemetry = {}
        while True:
            pid = _get_pid()
            is_running = bool(pid and _is_running(pid))
            tel = _read_json(TELEMETRY_FILE)
            if not tel and last_valid_telemetry:
                tel = last_valid_telemetry
            elif tel:
                last_valid_telemetry = tel

            
            # Logical override: If the backend wrote that it finished, force it to false
            if tel.get("status") in ["Completed", "Stopped by user", "CRASHED", "Idle (previous run ended unexpectedly)"]:
                is_running = False

            logs = get_log_tail(None)
            book = get_latest_book()
            preview = book.read_text(encoding="utf-8") if book else None
            is_live = book.name == "live_preview.md" if book else False

            payload = json.dumps({
                "is_running": is_running,
                "pid": pid,
                "telemetry": tel,
                "logs": logs,
                "preview": preview,
                "is_live": is_live,
                "ts": time.time()
            })
            yield f"data: {payload}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
