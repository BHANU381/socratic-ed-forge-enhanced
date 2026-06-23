import streamlit as st
import streamlit.components.v1 as components
import json
import os
import subprocess
import time
import shutil
import glob
import signal

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
PID_FILE = os.path.join(PROJECT_ROOT, "data", "runner.pid")

st.set_page_config(page_title="Socratic Ed-Forge Dashboard", layout="wide")

# Initialize Session State
if 'proc_running' not in st.session_state:
    st.session_state.proc_running = False
if 'process' not in st.session_state:
    st.session_state.process = None

# --- PID FILE RECOVERY: Reconnect to running process after browser refresh ---
if not st.session_state.proc_running and os.path.exists(PID_FILE):
    try:
        with open(PID_FILE, "r") as _f:
            _saved_pid = int(_f.read().strip())
        # Check if process with that PID is still alive
        os.kill(_saved_pid, 0)  # signal 0 = check existence only
        # It's alive - reconnect
        st.session_state.proc_running = True
        st.session_state.process = None  # can't restore handle, use PID kill
        st.session_state.reconnected_pid = _saved_pid
    except (OSError, ValueError):
        # Process is dead, clean up stale PID file
        os.remove(PID_FILE)
        st.session_state.proc_running = False

# Custom UI/UX Styles from ui-ux-pro-max-skill (Soft UI Evolution - Dark Mode)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

/* Global styles */
html, body, [class*="css"], .stApp {
    font-family: 'Fira Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #090615 !important;
    color: #E2E8F0 !important;
}

/* Header customization */
.main-title {
    font-family: 'Fira Sans', sans-serif !important;
    font-weight: 800 !important;
    color: #F5F3FF !important;
    font-size: 2.25rem !important;
    margin-bottom: 1.5rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.75rem !important;
}
.section-header {
    font-family: 'Fira Sans', sans-serif !important;
    font-weight: 700 !important;
    color: #DDD6FE !important;
    font-size: 1.5rem !important;
    margin-top: 1.5rem !important;
    margin-bottom: 1.25rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
    border-bottom: 2px solid #2A1E3E !important;
    padding-bottom: 0.5rem !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #120D25 !important;
    border-right: 1px solid #2A1E3E !important;
    box-shadow: 2px 0 12px rgba(139, 92, 246, 0.08) !important;
}
section[data-testid="stSidebar"] * {
    font-family: 'Fira Sans', sans-serif !important;
    color: #E2E8F0 !important;
}

/* Telemetry Bento Card & Grid */
.custom-card {
    background-color: #17122D !important;
    border: 1px solid #2A1E3E !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
    margin-bottom: 1.25rem !important;
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out !important;
}
.custom-card:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 25px rgba(139, 92, 246, 0.15) !important;
}

.bento-grid {
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 0.75rem !important;
    margin-bottom: 1rem !important;
}
@media (max-width: 768px) {
    .bento-grid {
        grid-template-columns: 1fr !important;
    }
}

.bento-cell {
    background-color: #241D44 !important;
    border: 1px solid #362A64 !important;
    border-radius: 8px !important;
    padding: 0.85rem !important;
    transition: all 0.2s ease-in-out !important;
}
.bento-cell:hover {
    background-color: #2C2353 !important;
    border-color: #8B5CF6 !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2) !important;
}

.bento-title {
    font-size: 0.75rem !important;
    color: #A78BFA !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-weight: 700 !important;
    margin-bottom: 0.25rem !important;
}
.bento-value {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: #F8FAFC !important;
}
.bento-value.status-running {
    color: #C084FC !important;
}
.bento-value.status-idle {
    color: #34D399 !important;
}

/* Developer Console Terminal Style for Logs */
.terminal-console {
    background-color: #04010A !important;
    border: 1px solid #241D44 !important;
    border-radius: 8px !important;
    padding: 1.25rem !important;
    font-family: 'Fira Code', monospace !important;
    font-size: 0.85rem !important;
    color: #F1F5F9 !important;
    height: 350px !important;
    overflow-y: auto !important;
    box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.8) !important;
    line-height: 1.6 !important;
    margin-bottom: 1.5rem !important;
}
.terminal-line {
    border-bottom: 1px solid #17122D !important;
    padding: 0.35rem 0 !important;
    white-space: pre-wrap !important;
}
.terminal-line:last-child {
    border-bottom: none !important;
}
.terminal-prompt {
    color: #34D399 !important;
    font-weight: bold !important;
}

/* Custom progress bar */
.stProgress > div > div > div > div {
    background-image: linear-gradient(90deg, #6366F1 0%, #8B5CF6 100%) !important;
    border-radius: 9999px !important;
}

/* Buttons Styling */
div.stButton > button {
    background-image: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 600 !important;
    font-family: 'Fira Sans', sans-serif !important;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2) !important;
    transition: all 0.2s ease-in-out !important;
    cursor: pointer !important;
    width: 100% !important;
}
div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 20px rgba(139, 92, 246, 0.35) !important;
    color: #FFFFFF !important;
}
div.stButton > button:active {
    transform: translateY(1px) !important;
    box-shadow: 0 3px 10px rgba(139, 92, 246, 0.15) !important;
}

/* Clear button override */
div.stButton > button[kind="secondary"] {
    background: #17122D !important;
    background-image: none !important;
    color: #C084FC !important;
    border: 1px solid #362A64 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
}
div.stButton > button[kind="secondary"]:hover {
    background: #241D44 !important;
    color: #E9D5FF !important;
    border-color: #8B5CF6 !important;
}

/* Live Book Preview Paper Style */
.preview-paper {
    background-color: #17122D !important;
    border: 1px solid #2A1E3E !important;
    border-radius: 12px !important;
    padding: 3rem 4rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
    font-family: 'Fira Sans', sans-serif !important;
    line-height: 1.7 !important;
    height: 780px !important;
    overflow-y: auto !important;
    color: #E2E8F0 !important;
    max-width: 900px !important;
    margin: 0 auto !important;
    text-align: justify !important;
}
.preview-paper h1, .preview-paper h2, .preview-paper h3 {
    font-family: 'Fira Sans', sans-serif !important;
    color: #F5F3FF !important;
    margin-top: 1.5rem !important;
    text-align: left !important;
}

/* File Uploader override */
section[data-testid="stFileUploader"] {
    border: 2px dashed #4C3D82 !important;
    background-color: #17122D !important;
    border-radius: 10px !important;
    padding: 1rem !important;
    transition: all 0.2s ease-in-out !important;
}
section[data-testid="stFileUploader"]:hover {
    border-color: #8B5CF6 !important;
    background-color: #241D44 !important;
}
section[data-testid="stFileUploader"] * {
    color: #E2E8F0 !important;
}

/* Expander custom styling */
div[data-testid="stExpander"] {
    background-color: #17122D !important;
    border: 1px solid #2A1E3E !important;
    border-radius: 8px !important;
}

/* Hide default Streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Fullscreen styles for textbook reader */
#live-book-preview-pane:fullscreen {
    background-color: #090615 !important;
    padding: 3rem !important;
    overflow-y: auto !important;
    height: 100% !important;
}
#live-book-preview-pane:fullscreen #fullscreen-toggle-btn {
    top: 2rem !important;
    right: 2rem !important;
}
</style>
""", unsafe_allow_html=True)

# Render Main Title
st.markdown('<div class="main-title"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6;"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg> Socratic Ed-Forge: Operations Center</div>', unsafe_allow_html=True)

# Sidebar Layout & Pacing Controls
st.sidebar.markdown('<div style="font-family: \'Fira Sans\', sans-serif; font-weight: 700; color: #F5F3FF; font-size: 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6;"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg> Dashboard Settings</div>', unsafe_allow_html=True)

show_fullscreen = st.sidebar.checkbox("📖 Fullscreen Preview Mode", value=False)

rpm_limit = st.sidebar.number_input(
    "Requests Per Minute (RPM) Limit",
    min_value=1,
    max_value=120,
    value=15,
    step=1,
    help="Maximum number of LLM API requests allowed per minute."
)
tpm_limit = st.sidebar.number_input(
    "Tokens Per Minute (TPM) Limit",
    min_value=1000,
    max_value=1000000,
    value=250000,
    step=10000,
    help="Maximum cumulative token count allowed per minute."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 Pedagogical Controls")
learner_level = st.sidebar.selectbox("Learner Level", ["beginner", "intermediate", "advanced"], index=0)
code_example_style = st.sidebar.selectbox("Code Example Style", ["progressive_production", "minimal", "practical", "production_first"], index=0)
explanation_depth = st.sidebar.selectbox("Explanation Depth", ["balanced", "concise", "deep"], index=0)
quality_profile = st.sidebar.selectbox("Quality Profile", ["standard", "light", "textbook"], index=0)
resume_run = st.sidebar.checkbox("🔄 Resume from last incomplete session", value=False)
st.sidebar.markdown("---")

# Debugging info
with st.expander("🔍 Debug Path Information"):
    st.write(f"**Detected Project Root:** `{PROJECT_ROOT}`")
    st.write(f"**Target Orchestrator:** `{SRC_MAIN}`")
    st.write(f"**Target Input Dir:** `{INPUT_DIR}`")
    st.write(f"**File exists?** `{'✅ Yes' if os.path.exists(SRC_MAIN) else '❌ NO'}`")

# Telemetry Loading Logic
def get_telemetry():
    default = {
        "status": "Idle", 
        "progress_percent": 0, 
        "current_agent": "None", 
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model_name": "N/A",
        "current_module": "N/A",
        "current_submodule": "N/A",
        "last_error_type": "None",
        "last_error_details": ""
    }
    if os.path.exists(TELEMETRY_FILE):
        try:
            with open(TELEMETRY_FILE, "r") as f:
                data = json.load(f)
                for key in default.keys():
                    if key not in data:
                        data[key] = default[key]
                return data
        except:
            pass
    return default

def display_telemetry_ui(tel):
    status = tel.get("status", "Unknown")
    is_active = status.lower() not in ["idle", "finished", "success", "error", "failed", "stopped"]
    status_class = "status-running" if is_active else "status-idle"
    
    inp_tok = tel.get('input_tokens', 0)
    out_tok = tel.get('output_tokens', 0)
    tot_tok = tel.get('total_tokens', 0)
    progress_val = tel.get("progress_percent", 0)
    
    html_content = f"""<div class="custom-card">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
<div style="font-weight: 700; color: #F5F3FF; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line><line x1="15" y1="3" x2="15" y2="21"></line><line x1="3" y1="9" x2="21" y2="9"></line><line x1="3" y1="15" x2="21" y2="15"></line></svg>
Operational Insights
</div>
<span class="bento-value {status_class}" style="font-size: 0.85rem; padding: 0.25rem 0.75rem; border-radius: 9999px; background-color: #241D44; font-weight: 700; border: 1px solid #362A64;">{status}</span>
</div>
<div class="bento-grid">
<div class="bento-cell">
<div class="bento-title">Active Agent</div>
<div class="bento-value" style="font-size: 1.05rem; color: #C084FC; word-break: break-all;">{tel.get('current_agent', 'None')}</div>
</div>
<div class="bento-cell">
<div class="bento-title">Model Name</div>
<div class="bento-value" style="font-size: 0.95rem; word-break: break-all; color: #94A3B8;">{tel.get('model_name', 'N/A')}</div>
</div>
<div class="bento-cell">
<div class="bento-title">Completion</div>
<div class="bento-value" style="font-size: 1.25rem;">{progress_val}%</div>
</div>
<div class="bento-cell">
<div class="bento-title">Total Tokens</div>
<div class="bento-value" style="font-size: 1.25rem; color: #8B5CF6;">{tot_tok:,}</div>
</div>
</div>
<div style="margin: 0.5rem 0 1rem 0;">
<div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: #94A3B8; margin-bottom: 0.35rem;">
<span>Input: {inp_tok:,}</span>
<span>Output: {out_tok:,}</span>
</div>
</div>
<div style="border-top: 1px solid #2A1E3E; padding-top: 0.85rem; margin-top: 0.5rem; font-size: 0.88rem;">
<div style="color: #8B5CF6; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;">Current Goal</div>
<div style="font-weight: 600; color: #E2E8F0;"><b>Module:</b> {tel.get('current_module', 'N/A')}</div>
<div style="font-weight: 500; color: #94A3B8; margin-top: 0.2rem;"><b>Submodule:</b> {tel.get('current_submodule', 'N/A')}</div>
</div>
</div>"""
    st.markdown(html_content, unsafe_allow_html=True)
    st.progress(progress_val / 100)

    # 5. Render Audit & Critique Alert Card
    last_error_type = tel.get("last_error_type", "None")
    last_error_details = tel.get("last_error_details", "")
    
    if last_error_type != "None" and last_error_details:
        details_html = ""
        for line in last_error_details.strip().split("\n"):
            if line.strip().startswith("-"):
                details_html += f'<div style="margin-left: 0.5rem; margin-bottom: 0.25rem; color: #FDA4AF;">• {line.strip()[1:].strip()}</div>'
            else:
                details_html += f'<div style="margin-bottom: 0.25rem; color: #F1F5F9;">{line}</div>'
                
        alert_html = f"""<div class="custom-card" style="border-color: #EF4444 !important; background-color: #2D142C !important; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.15) !important;">
<div style="font-weight: 700; color: #F87171; font-size: 1rem; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;">
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #F87171;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
Audit Alert: {last_error_type}
</div>
<div style="font-family: 'Fira Code', monospace; font-size: 0.82rem; line-height: 1.5; max-height: 180px; overflow-y: auto; color: #E2E8F0;">
{details_html}
</div>
</div>"""
        st.markdown(alert_html, unsafe_allow_html=True)

# Non-blocking Process State Monitoring Check
if st.session_state.get('proc_running', False):
    process = st.session_state.get('process')
    pid = st.session_state.get('reconnected_pid')
    finished = False
    exit_code = 0

    if process:
        poll = process.poll()
        if poll is not None:
            finished = True
            exit_code = poll
    elif pid:
        # Reconnected via PID file - check if still alive
        try:
            os.kill(pid, 0)
        except OSError:
            finished = True
            exit_code = 0

    if finished:
        st.session_state.proc_running = False
        st.session_state.process = None
        st.session_state.reconnected_pid = None
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                if exit_code == 0:
                    f.write(f"[{time.strftime('%H:%M:%S')}] **System**: Course generation pipeline finished successfully.\n")
                else:
                    f.write(f"[{time.strftime('%H:%M:%S')}] **System**: Process exited with error code {exit_code}.\n")
        tel = get_telemetry()
        tel["status"] = "Finished" if exit_code == 0 else f"Failed (Exit {exit_code})"
        tel["current_agent"] = "None"
        with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
            json.dump(tel, f, indent=4)
        st.rerun()

# Layout: Split screen or Fullscreen Preview
if show_fullscreen:
    # Fullscreen Preview Layout
    with st.expander("📊 Show Running Status & Telemetry"):
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            tel = get_telemetry()
            display_telemetry_ui(tel)
        with col_t2:
            # Render a summary logs terminal console
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    escaped_lines = []
                    for line in lines:
                        clean = line.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        escaped_lines.append(f'<div class="terminal-line"><span class="terminal-prompt">&gt;</span> {clean}</div>')
                    log_html = "".join(escaped_lines)
                    st.markdown(f'<div id="terminal-console-box" class="terminal-console" style="height: 180px !important;">{log_html}</div><script>var obj = document.getElementById("terminal-console-box"); if(obj) {{ obj.scrollTop = obj.scrollHeight; }}</script>', unsafe_allow_html=True)

    st.markdown('<div class="section-header"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #6366F1; vertical-align: middle;"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg> Live Book Preview (Fullscreen Mode)</div>', unsafe_allow_html=True)
    preview_placeholder = st.empty()
else:
    # Split screen (Standard Dashboard Layout)
    col1, col2 = st.columns([1.1, 1.9])
    
    with col1:
        st.markdown('<div class="section-header"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #6366F1; vertical-align: middle;"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg> System Telemetry</div>', unsafe_allow_html=True)
        
        # Telemetry UI
        tel = get_telemetry()
        display_telemetry_ui(tel)
        
        st.divider()
        
        st.markdown('<div class="section-header"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #6366F1; vertical-align: middle;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> Agent Logs</div>', unsafe_allow_html=True)
        
        # Action Buttons Layout
        col_actions1, col_actions2 = st.columns(2)
        with col_actions1:
            if st.button("🧹 Clear Logs"):
                if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
                if os.path.exists(TELEMETRY_FILE): os.remove(TELEMETRY_FILE)
                st.rerun()
                
        with col_actions2:
            if st.session_state.get('proc_running', False):
                if st.button("🛑 Stop Loop"):
                    process = st.session_state.get('process')
                    pid = st.session_state.get('reconnected_pid')
                    if process:
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    elif pid:
                        try:
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(1)
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass
                    
                    st.session_state.proc_running = False
                    st.session_state.process = None
                    st.session_state.reconnected_pid = None
                    if os.path.exists(PID_FILE):
                        os.remove(PID_FILE)
                    
                    if os.path.exists(LOG_FILE):
                        with open(LOG_FILE, "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%H:%M:%S')}] **System**: Generation stopped by user.\n")
                    
                    tel = get_telemetry()
                    tel["status"] = "Stopped"
                    tel["current_agent"] = "None"
                    with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
                        json.dump(tel, f, indent=4)
                    
                    st.success("Stopped successfully!")
                    time.sleep(1)
                    st.rerun()
        
        # Start Actions (Hide uploader/start button when active)
        if not st.session_state.get('proc_running', False):
            uploaded_file = st.file_uploader("Upload JSON Config", type="json")
            if uploaded_file and st.button("🚀 Start Production"):
                os.makedirs(INPUT_DIR, exist_ok=True)
                try:
                    file_bytes = uploaded_file.getvalue()
                    data = json.loads(file_bytes.decode('utf-8'))
                    
                    # Inject custom parameters from select boxes
                    data["learner_level"] = learner_level
                    data["code_example_style"] = code_example_style
                    data["explanation_depth"] = explanation_depth
                    data["quality_profile"] = quality_profile
                    
                    with open(os.path.join(INPUT_DIR, "course_input.json"), "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    
                    # Reset telemetry on start
                    init_telemetry = {
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
                    with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
                        json.dump(init_telemetry, f, indent=4)
                        
                    # Wipe log file for a clean start
                    if os.path.exists(LOG_FILE):
                        os.remove(LOG_FILE)
                        
                    st.success("Config Uploaded Successfully!")
                except Exception as e:
                    st.error(f"Upload Failed: {e}")
                    st.stop()
                
                # Launch background process asynchronously
                env = os.environ.copy()
                env["PYTHONPATH"] = PROJECT_ROOT
                env["RPM_LIMIT"] = str(rpm_limit)
                env["TPM_LIMIT"] = str(tpm_limit)
                env["RUN_TYPE"] = "resume_existing_run" if resume_run else "new_run"
                
                process = subprocess.Popen(
                    ["python", "-m", "src.engine.orchestrator"], 
                    cwd=PROJECT_ROOT,
                    env=env
                )
                # Write PID to file so stop button survives browser refresh
                with open(PID_FILE, "w") as _pf:
                    _pf.write(str(process.pid))
                st.session_state.process = process
                st.session_state.proc_running = True
                st.session_state.reconnected_pid = None
                st.rerun()
        else:
            st.info("Generation loop running... Click '🛑 Stop Loop' to cancel.")
        
        # Render scrollable terminal log console
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                escaped_lines = []
                for line in lines:
                    clean = line.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    escaped_lines.append(f'<div class="terminal-line"><span class="terminal-prompt">&gt;</span> {clean}</div>')
                log_html = "".join(escaped_lines)
                st.markdown(f'<div id="terminal-console-box" class="terminal-console">{log_html}</div><script>var obj = document.getElementById("terminal-console-box"); if(obj) {{ obj.scrollTop = obj.scrollHeight; }}</script>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="terminal-console"><div class="terminal-line"><span class="terminal-prompt">&gt;</span> System idle. Upload a JSON config and launch production to see live logs.</div></div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-header"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #6366F1; vertical-align: middle;"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg> Live Book Preview</div>', unsafe_allow_html=True)
        preview_placeholder = st.empty()

# Live Book Preview Rendering Logic
def get_latest_book():
    session_dirs = glob.glob(os.path.join(OUTPUT_DIR, "session_*"))
    if not session_dirs:
        return None
    latest_session = max(session_dirs, key=os.path.getmtime)
    
    live_preview = os.path.join(latest_session, "live_preview.md")
    if os.path.exists(live_preview):
        return live_preview
        
    md_files = glob.glob(os.path.join(latest_session, "*.md"))
    # Exclude live_preview.md from fallback glob just in case
    md_files = [f for f in md_files if not os.path.basename(f) == "live_preview.md"]
    if md_files:
        return max(md_files, key=os.path.getmtime)
    return None

latest_book = get_latest_book()

# ── Preview Rendering ────────────────────────────────────────────────────────
# Renders markdown DIRECTLY into Streamlit's main page via st.markdown().
# No iframe, no fixed-height container. Streamlit preserves the main page
# scroll position across st.rerun() natively via React DOM reconciliation.

PREVIEW_CSS = """
<style>
/* Live-book preview typography injected into Streamlit's main DOM */
.preview-md-root { padding: 0.25rem 0.5rem 3rem 0.5rem; }
.preview-md-root h1 { color:#F5F3FF; font-size:1.6rem; margin:0 0 0.65rem; line-height:1.3; font-weight:700; }
.preview-md-root h2 { color:#EDE9FE; font-size:1.15rem; margin:1.9rem 0 0.45rem;
  border-bottom:1px solid #241D44; padding-bottom:0.4rem; font-weight:600; }
.preview-md-root h3 { color:#DDD6FE; font-size:0.97rem; margin:1.3rem 0 0.3rem; font-weight:600; }
.preview-md-root h4 { color:#C4B5FD; font-size:0.88rem; margin:0.9rem 0 0.25rem; font-weight:600; }
.preview-md-root p  { margin-bottom:0.8rem; color:#CBD5E1; line-height:1.8; font-size:0.93rem; }
.preview-md-root strong { color:#F1F5F9; }
.preview-md-root em { color:#94A3B8; }
.preview-md-root ul, .preview-md-root ol { margin:0.35rem 0 0.8rem 1.5rem; }
.preview-md-root li { margin-bottom:0.3rem; color:#CBD5E1; font-size:0.92rem; line-height:1.7; }
.preview-md-root code {
  background:#1C1533; color:#C084FC; padding:0.12em 0.42em;
  border-radius:4px; font-family:'Fira Code',monospace; font-size:0.84em;
  border:1px solid #2A1E3E; }
.preview-md-root pre {
  background:#04010A; border:1px solid #241D44; border-radius:8px;
  padding:1rem 1.15rem; overflow-x:auto; margin:0.9rem 0; }
.preview-md-root pre code { background:none; color:#94A3B8; padding:0; border:none; }
.preview-md-root blockquote {
  border-left:3px solid #6366F1; padding:0.5rem 1rem; color:#94A3B8;
  margin:0.9rem 0; background:#13102A; border-radius:0 6px 6px 0; }
.preview-md-root hr { border:none; border-top:1px solid #1E1A30; margin:1.6rem 0; }
.preview-md-root a { color:#818CF8; text-decoration:none; }
.preview-md-root a:hover { color:#A78BFA; text-decoration:underline; }
.preview-md-root table { width:100%; border-collapse:collapse; margin:0.9rem 0; font-size:0.88rem; }
.preview-md-root th { background:#1A1430; color:#DDD6FE; padding:0.55rem 0.8rem;
  text-align:left; border-bottom:2px solid #2A1E3E; }
.preview-md-root td { padding:0.5rem 0.8rem; border-bottom:1px solid #1A1430; color:#CBD5E1; }
.preview-md-root tr:hover td { background:#13102A; }
.live-badge {
  display:inline-flex; align-items:center; gap:0.4rem;
  background:#241D44; border:1px solid #362A64; border-radius:9999px;
  padding:0.22rem 0.7rem; font-size:0.72rem; color:#C084FC; font-weight:700;
  margin-bottom:1rem; letter-spacing:0.05em;
}
.live-badge-dot {
  width:6px; height:6px; border-radius:50%; background:#C084FC;
  animation: livepulse 1.2s infinite;
}
@keyframes livepulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
</style>
"""

def render_preview(book_path):
    if book_path:
        with open(book_path, "r", encoding="utf-8") as f:
            book_content = f.read()
        is_live = os.path.basename(book_path) == "live_preview.md"
        live_badge = (
            '<span class="live-badge">'
            '<span class="live-badge-dot"></span>LIVE DRAFT'
            '</span>'
        ) if is_live else ""
        preview_placeholder.markdown(
            PREVIEW_CSS +
            f'<div class="preview-md-root">{live_badge}\n\n' +
            book_content +
            '</div>',
            unsafe_allow_html=True
        )
    else:
        preview_placeholder.markdown(
            '<p style="color:#4B5563;font-style:italic;padding:1rem 0;">'
            'Waiting for production to start...</p>',
            unsafe_allow_html=True
        )

render_preview(latest_book)

# Continuous Refresh loop trigger (1 second refresh when active, 5 seconds when idle)
if st.session_state.get('proc_running', False):
    time.sleep(1)
    st.rerun()
elif latest_book:
    time.sleep(5)
    st.rerun()

    if book_path:
        with open(book_path, "r", encoding="utf-8") as f:
            raw_md = f.read()
        # Escape backticks for JS template literal
        raw_md_escaped = raw_md.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
        # Determine if this is a live draft
        is_live = os.path.basename(book_path) == "live_preview.md"
        live_badge = (
            '<div style="display:inline-flex;align-items:center;gap:0.4rem;'
            'background:#241D44;border:1px solid #362A64;border-radius:9999px;'
            'padding:0.25rem 0.75rem;font-size:0.75rem;color:#C084FC;font-weight:700;'
            'margin-bottom:1rem;">'
            '<span style="width:7px;height:7px;border-radius:50%;background:#C084FC;'
            'animation:pulse 1.2s infinite;display:inline-block;"></span>LIVE DRAFT</div>'
        ) if is_live else ""

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #17122D;
    color: #E2E8F0;
    font-family: 'Fira Sans', sans-serif;
    font-size: 15px;
    line-height: 1.75;
    padding: 1.75rem 2rem 3rem 2rem;
    overflow-y: auto;
    height: 100vh;
  }}
  h1,h2,h3,h4 {{ color:#F5F3FF; margin:1.5rem 0 0.5rem; }}
  h3 {{ color:#DDD6FE; font-size:1.05rem; border-bottom:1px solid #2A1E3E; padding-bottom:0.35rem; }}
  p {{ margin-bottom: 0.85rem; }}
  code {{ background:#241D44; color:#C084FC; padding:0.15em 0.4em; border-radius:4px; font-family:'Fira Code',monospace; font-size:0.88em; }}
  pre {{ background:#04010A; border:1px solid #241D44; border-radius:8px; padding:1rem; overflow-x:auto; margin:1rem 0; }}
  pre code {{ background:none; color:#94A3B8; padding:0; }}
  ul,ol {{ margin:0.5rem 0 0.85rem 1.5rem; }}
  li {{ margin-bottom:0.3rem; }}
  strong {{ color:#F8FAFC; }}
  blockquote {{ border-left:3px solid #6366F1; padding-left:1rem; color:#94A3B8; margin:1rem 0; }}
  hr {{ border:none; border-top:1px solid #2A1E3E; margin:1.5rem 0; }}
  @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
  #fs-btn {{
    position: fixed; top: 1rem; right: 1rem;
    background: rgba(36,29,68,0.9); border: 1px solid #362A64;
    border-radius: 6px; color: #E2E8F0; padding: 0.45rem 0.6rem;
    cursor: pointer; z-index: 9999; transition: all 0.2s;
    display: flex; align-items: center; justify-content: center;
  }}
  #fs-btn:hover {{ background:#8B5CF6; border-color:#8B5CF6; }}
</style>
</head>
<body>
<button id="fs-btn" title="Toggle Fullscreen"
  onclick="if(!document.fullscreenElement){{document.documentElement.requestFullscreen();}}else{{document.exitFullscreen();}}">
  <svg id="fs-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
  </svg>
</button>
{live_badge}
<div id="content"></div>
<script>
  var md = `{raw_md_escaped}`;
  document.getElementById("content").innerHTML = marked.parse(md);
  document.addEventListener('fullscreenchange', function() {{
    var ic = document.getElementById('fs-icon');
    if (document.fullscreenElement) {{
      ic.innerHTML = '<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7"/>';
    }} else {{
      ic.innerHTML = '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>';
    }}
  }});
</script>
</body>
</html>"""
    else:
        html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400&display=swap" rel="stylesheet">
<style>body{{background:#17122D;color:#64748B;font-family:'Fira Sans',sans-serif;
display:flex;align-items:center;justify-content:center;height:100vh;font-style:italic;font-size:0.95rem;}}</style>
</head><body>Waiting for production to start...</body></html>"""

    preview_placeholder.empty()
    with preview_placeholder.container():
        components.html(html, height=height, scrolling=False)

render_preview(latest_book)

# Continuous Refresh loop trigger (1 second refresh when active, 5 seconds when idle)
if st.session_state.get('proc_running', False):
    time.sleep(1)
    st.rerun()
elif latest_book:
    time.sleep(5)
    st.rerun()

