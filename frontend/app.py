import streamlit as st
import json
import os
import subprocess
import time
import shutil
import glob

# Absolute Project Root
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)

# FIX: app.py is in 'frontend/', so we only need to go up ONE level to reach the project root
PROJECT_ROOT = os.path.abspath(os.path.join(_current_dir, ".."))

# Verify Project Root - If 'src' isn't here, we are in the wrong place
if not os.path.exists(os.path.join(PROJECT_ROOT, "src")):
    # Fallback/Safety check
    PROJECT_ROOT = os.path.abspath(os.path.join(_current_dir, "..", ".."))

INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "input")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")
LOG_FILE = os.path.join(PROJECT_ROOT, "data", "logs.txt")
TELEMETRY_FILE = os.path.join(PROJECT_ROOT, "data", "telemetry.json")
SRC_MAIN = os.path.join(PROJECT_ROOT, "src", "engine", "orchestrator.py")

st.set_page_config(page_title="Socratic Ed-Forge Dashboard", layout="wide")
st.title("🛠️ Socratic Ed-Forge: Operations Center")

# Debugging info for the user (can be removed later)
with st.expander("🔍 Debug Path Information"):
    st.write(f"**Detected Project Root:** `{PROJECT_ROOT}`")
    st.write(f"**Target Orchestrator:** `{SRC_MAIN}`")
    st.write(f"**Target Input Dir:** `{INPUT_DIR}`")
    st.write(f"**File exists?** `{'✅ Yes' if os.path.exists(SRC_MAIN) else '❌ NO'}`")

# Layout: Split screen
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📊 System Telemetry")
    
    # Telemetry Widgets
    telemetry_placeholder = st.empty()
    
    def get_telemetry():
        if os.path.exists(TELEMETRY_FILE):
            try:
                with open(TELEMETRY_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"status": "Idle", "progress_percent": 0, "current_agent": "None", "total_tokens": 0}

    tel = get_telemetry()
    
    with telemetry_placeholder.container():
        st.metric("Status", tel.get("status", "Unknown"))
        st.progress(tel.get("progress_percent", 0) / 100)
        st.write(f"**Progress:** {tel.get('progress_percent', 0)}%")
        st.write(f"**Active Agent:** `{tel.get('current_agent', 'None')}`")
        st.write(f"**Tokens Used:** `{tel.get('total_tokens', 0)}`")
        st.write(f"**Module:** `{tel.get('current_module', 'N/A')}`")
        st.write(f"**Submodule:** `{tel.get('current_submodule', 'N/A')}`")

    st.divider()

    st.header("📜 Agent Logs")
    if st.button("🗑️ Reset All"):
        if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
        if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        if os.path.exists(TELEMETRY_FILE): os.remove(TELEMETRY_FILE)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        st.rerun()

    uploaded_file = st.file_uploader("Upload JSON Config", type="json")
    if uploaded_file and st.button("🚀 Start Production"):
        os.makedirs(INPUT_DIR, exist_ok=True)
        
        # Bypass Streamlit's temporary file storage to prevent 403 errors
        try:
            file_bytes = uploaded_file.getvalue()
            with open(os.path.join(INPUT_DIR, "course_input.json"), "wb") as f:
                f.write(file_bytes)
            st.success("Config Uploaded Successfully!")
        except Exception as e:
            st.error(f"Upload Failed: {e}")
            st.stop()
        
        # Launch process
        # FIX: Explicitly pass PYTHONPATH to include PROJECT_ROOT so 'src' is findable
        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT
        
        process = subprocess.Popen(
            ["python", "-m", "src.engine.orchestrator"], 
            cwd=PROJECT_ROOT,
            env=env
        )
        st.session_state.proc_running = True
        
        log_display = st.empty()
        while process.poll() is None:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-20:]
                    with log_display.container():
                        for line in lines:
                            st.write(line.strip())
            time.sleep(1)
        st.success("Loop Finished!")
        st.session_state.proc_running = False

with col2:
    st.header("📖 Live Book Preview")
    preview_placeholder = st.empty()
    
    def get_latest_book():
        files = glob.glob(os.path.join(OUTPUT_DIR, "*.md"))
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    latest_book = get_latest_book()

    if latest_book:
        with open(latest_book, "r", encoding="utf-8") as f:
            preview_placeholder.markdown(f.read())
    else:
        preview_placeholder.info("Waiting for production to start...")

    # Continuous Refresh logic
    if st.session_state.get('proc_running', False):
        time.sleep(2)
        st.rerun()
    elif latest_book:
        time.sleep(3)
        st.rerun()
