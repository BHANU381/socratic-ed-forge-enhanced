import streamlit as st
import json
import os
import subprocess
import time
import shutil
import glob

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "input")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")
LOG_FILE = os.path.join(PROJECT_ROOT, "data", "logs.txt")
SRC_MAIN = os.path.join(PROJECT_ROOT, "src", "main.py")

st.set_page_config(page_title="Agentic Loop Dashboard", layout="wide")
st.title("AI Course Generator: Agentic Loop")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Agent Logs")
    if st.button("🗑️ Reset All"):
        if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
        if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        st.rerun()

    uploaded_file = st.file_uploader("Upload JSON Config", type="json")
    if uploaded_file and st.button("🚀 Run Loop"):
        os.makedirs(INPUT_DIR, exist_ok=True)
        with open(os.path.join(INPUT_DIR, "course_input.json"), "w") as f:
            json.dump(json.loads(uploaded_file.getvalue().decode("utf-8")), f)
        
        # Fixed: Run the main script as a module from the root
        process = subprocess.Popen(["python", "-m", "src.main"], cwd=PROJECT_ROOT)
        
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

with col2:
    st.header("Live Preview")
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
        preview_placeholder.info("Waiting for generation to start... (No files found in output)")

    # Auto-refresh logic
    time.sleep(2)
    st.rerun()
