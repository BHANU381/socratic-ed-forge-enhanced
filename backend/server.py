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

load_dotenv()

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
            
        # Validate schema using Pydantic
        from src.models.schemas import CourseInput
        CourseInput.model_validate(data)
        
        # Rewrite the modified data to file_bytes to be saved
        file_bytes = json.dumps(data, indent=4).encode('utf-8')
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            raise HTTPException(status_code=422, detail=f"Schema Validation Failed: {e.errors()}")
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

# ── SSE Stream ────────────────────────────────────────────────────────────────
@app.get("/api/stream")
async def stream(interval: float = 1.5):
    """
    Server-Sent Events stream. Client connects once;
    server pushes updates. No polling loop needed in the UI.
    """
    async def event_generator():
        while True:
            pid = _get_pid()
            is_running = bool(pid and _is_running(pid))
            tel = _read_json(TELEMETRY_FILE)
            
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
