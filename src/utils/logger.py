import glob
import os
import json
import datetime
from dotenv import load_dotenv

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
