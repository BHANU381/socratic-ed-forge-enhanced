import json
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def log_event(role: str, message: str, session_dir: Optional[str] = None) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    log_entry = f"[{ts}] **{role}**: {clean_message}\n"
    
    # Print to the terminal console so the user can track progress in the backend terminal
    print(f"[{ts}] {role}: {clean_message}", flush=True)
    
    # Always write to global log file
    global_log_file = PROJECT_ROOT / 'data' / 'logs.txt'
    global_log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with global_log_file.open('a', encoding='utf-8') as f:
        f.write(log_entry)
        f.flush()
        os.fsync(f.fileno())
        
    # Also write to session-specific log file if provided
    if session_dir:
        session_log_file = Path(session_dir) / 'session_logs.txt'
        session_log_file.parent.mkdir(parents=True, exist_ok=True)
        with session_log_file.open('a', encoding='utf-8') as f:
            f.write(log_entry)
            f.flush()
            os.fsync(f.fileno())

def update_status(message: str, session_dir: Optional[str] = None) -> None:
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    
    # Always write to global status file
    global_status_file = PROJECT_ROOT / 'data' / 'status.txt'
    global_status_file.parent.mkdir(parents=True, exist_ok=True)
    with global_status_file.open('w', encoding='utf-8') as f:
        f.write(clean_message)
        f.flush()
        os.fsync(f.fileno())
        
    # Also write to session-specific status file if provided
    if session_dir:
        session_status_file = Path(session_dir) / 'status.txt'
        session_status_file.parent.mkdir(parents=True, exist_ok=True)
        with session_status_file.open('w', encoding='utf-8') as f:
            f.write(clean_message)
            f.flush()
            os.fsync(f.fileno())

def update_telemetry(data: Dict[str, Any], session_dir: Optional[str] = None, telemetry_file_path: Optional[str] = None) -> None:
    """Writes real-time telemetry to a JSON file for the dashboard."""
    telemetry_file = Path(telemetry_file_path) if telemetry_file_path else PROJECT_ROOT / 'data' / 'telemetry.json'
    data['timestamp'] = datetime.datetime.now().isoformat()
    if session_dir:
        data['session_dir'] = str(session_dir)
        
    # Write to global telemetry file
    try:
        telemetry_file.parent.mkdir(parents=True, exist_ok=True)
        with telemetry_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Telemetry Error: {e}")
        
    # Also write to session-specific telemetry file if provided
    if session_dir:
        session_telemetry_file = Path(session_dir) / 'telemetry.json'
        try:
            session_telemetry_file.parent.mkdir(parents=True, exist_ok=True)
            with session_telemetry_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"Session Telemetry Error: {e}")
