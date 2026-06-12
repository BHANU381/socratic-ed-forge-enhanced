import glob
import os
import json
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Project Root relative to this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def log_event(role, message, session_dir=None):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    log_entry = f"[{ts}] **{role}**: {clean_message}\n"
    
    # Print to the terminal console so the user can track progress in the backend terminal
    print(f"[{ts}] {role}: {clean_message}", flush=True)
    
    # Always write to global log file
    global_log_file = os.path.join(PROJECT_ROOT, 'data', 'logs.txt')
    os.makedirs(os.path.dirname(global_log_file), exist_ok=True)
    with open(global_log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
        f.flush()
        os.fsync(f.fileno())
        
    # Also write to session-specific log file if provided
    if session_dir:
        session_log_file = os.path.join(session_dir, 'session_logs.txt')
        os.makedirs(os.path.dirname(session_log_file), exist_ok=True)
        with open(session_log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            f.flush()
            os.fsync(f.fileno())

def update_status(message, session_dir=None):
    clean_message = message.encode('ascii', 'ignore').decode('ascii')
    
    # Always write to global status file
    global_status_file = os.path.join(PROJECT_ROOT, 'data', 'status.txt')
    os.makedirs(os.path.dirname(global_status_file), exist_ok=True)
    with open(global_status_file, 'w', encoding='utf-8') as f:
        f.write(clean_message)
        f.flush()
        os.fsync(f.fileno())
        
    # Also write to session-specific status file if provided
    if session_dir:
        session_status_file = os.path.join(session_dir, 'status.txt')
        os.makedirs(os.path.dirname(session_status_file), exist_ok=True)
        with open(session_status_file, 'w', encoding='utf-8') as f:
            f.write(clean_message)
            f.flush()
            os.fsync(f.fileno())

def update_telemetry(data, session_dir=None, telemetry_file_path=None):
    """Writes real-time telemetry to a JSON file for the dashboard."""
    telemetry_file = telemetry_file_path or os.path.join(PROJECT_ROOT, 'data', 'telemetry.json')
    data['timestamp'] = datetime.datetime.now().isoformat()
    if session_dir:
        data['session_dir'] = session_dir
        
    # Write to global telemetry file
    try:
        with open(telemetry_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Telemetry Error: {e}")
        
    # Also write to session-specific telemetry file if provided
    if session_dir:
        session_telemetry_file = os.path.join(session_dir, 'telemetry.json')
        try:
            with open(session_telemetry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"Session Telemetry Error: {e}")
