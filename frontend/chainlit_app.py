import os
import json
import glob
import asyncio
import chainlit as cl
from pathlib import Path
import anyio

def resolve_project_paths(current_file_path):
    """
    Resolves absolute paths for project root, input, and output directories
    based on the location of the current file.
    """
    current_file = Path(current_file_path).resolve()
    project_root = current_file.parent.parent
    
    input_dir = project_root / "data" / "input"
    output_dir = project_root / "data" / "output"
    telemetry_file = project_root / "telemetry.json"
    log_file = project_root / "logs.txt"
    
    return project_root, input_dir, output_dir, telemetry_file, log_file

async def get_telemetry_data(telemetry_file):
    """
    Parses the telemetry.json file and returns a dictionary.
    """
    default = {
        "status": "Idle", 
        "progress_percent": 0, 
        "current_agent": "None", 
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model_name": "N/A",
        "current_module": "N/A"
    }
    
    if not os.path.exists(telemetry_file):
        return default
        
    try:
        # Use anyio to ensure this is non-blocking and loop-safe
        content = await anyio.to_thread.run_sync(lambda: open(telemetry_file, "r").read())
        data = json.loads(content)
        for key, value in default.items():
            if key not in data:
                data[key] = value
        return data
    except Exception:
        return default

async def get_latest_book_path(output_dir):
    """
    Finds the most recently modified Markdown file.
    """
    search_pattern = os.path.join(output_dir, "session_*", "*.md")
    
    # Wrap glob in to_thread to prevent loop blocking
    files = await anyio.to_thread.run_sync(lambda: glob.glob(search_pattern))
    
    if not files:
        return None
        
    # Wrap mtime in to_thread
    return await anyio.to_thread.run_sync(lambda: max(files, key=os.path.getmtime))

async def get_latest_log_lines(log_file, n=20):
    """
    Reads the last n lines of a log file.
    """
    if not os.path.exists(log_file):
        return "No logs available."
    try:
        def read_tail():
            with open(log_file, "r") as f:
                lines = f.readlines()
                return "".join(lines[-n:])
        return await anyio.to_thread.run_sync(read_tail)
    except Exception as e:
        return f"Error reading logs: {str(e)}"

# --- Chainlit UI Implementation ---

@cl.on_chat_start
async def start():
    # 1. Cleanup any existing tasks (Safety First)
    existing_task = cl.user_session.get("monitor_task")
    if existing_task:
        existing_task.cancel()
        try:
            await existing_task
        except asyncio.CancelledError:
            pass

    # 2. Setup Paths
    project_root, input_dir, output_dir, tel_file, log_file = resolve_project_paths(__file__)
    cl.user_session.set("paths", {
        "root": project_root,
        "input": input_dir,
        "output": output_dir,
        "telemetry": tel_file,
        "logs": log_file
    })
    cl.user_session.set("running", False)

    # 3. Initialize UI Elements
    telemetry_msg = cl.Message(content="📊 **System Telemetry**\nInitializing...")
    await telemetry_msg.send()
    cl.user_session.set("telemetry_msg", telemetry_msg)

    log_msg = cl.Message(content="📜 **Live Engine Logs**\nWaiting for activity...")
    await log_msg.send()
    cl.user_session.set("log_msg", log_msg)

    book_msg = cl.Message(content="📖 **Latest Generated Book**\nNo books found yet.")
    await book_msg.send()
    cl.user_session.set("book_msg", book_msg)

    # 4. Start Background Monitoring Loop
    # We wrap this in a task and store it so we can cancel it later
    monitor_task = asyncio.create_task(monitor_loop())
    cl.user_session.set("monitor_task", monitor_task)

    await cl.Message(content="🚀 **Socratic Ed-Forge Dashboard Online.**\n\nUse the chat to send commands like `start`, `stop`, or `status`.").send()

@cl.on_chat_end
async def on_end():
    """
    CRITICAL: Cleanup background tasks when the user leaves the session.
    This prevents the 'Ghost Task' problem that causes NoEventLoopError.
    """
    monitor_task = cl.user_session.get("monitor_task")
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

async def monitor_loop():
    """
    Background task that periodically updates the telemetry, logs, and book preview.
    """
    paths = cl.user_session.get("paths")
    tel_msg = cl.user_session.get("telemetry_msg")
    log_msg = cl.user_session.get("log_msg")
    book_msg = cl.user_session.get("book_msg")

    try:
        while True:
            # Update Telemetry
            tel_data = await get_telemetry_data(str(paths["telemetry"]))
            tel_text = (
                f"**Status:** `{tel_data['status']}`\n"
                f"**Agent:** `{tel_data['current_agent']}`\n"
                f"**Module:** `{tel_data['current_module']}`\n"
                f"**Progress:** `{tel_data['progress_percent']}%`\n"
                f"**Tokens:** 📥 `{tel_data['input_tokens']}` | 📤 `{tel_data['output_tokens']}` | 🔄 `{tel_data['total_tokens']}`\n"
                f"**Model:** `{tel_data['model_name']}`"
            )
            await tel_msg.update(content=f"📊 **System Telemetry**\n{tel_text}")

            # Update Logs
            logs = await get_latest_log_lines(str(paths["logs"]))
            await log_msg.update(content=f"📜 **Live Engine Logs**\n```text\n{logs}\n```")

            # Update Book Preview
            latest_book = await get_latest_book_path(str(paths["output"]))
            if latest_book:
                content = await anyio.to_thread.run_sync(lambda: open(latest_book, "r").read())
                preview = content[:1000] + ("..." if len(content) > 1000 else "")
                await book_msg.update(content=f"📖 **Latest Generated Book**\n\n**File:** `{os.path.basename(latest_book)}`\n\n---\n\n{preview}")
            else:
                await book_msg.update(content="📖 **Latest Generated Book**\n\nNo books found yet.")

            await asyncio.sleep(3)
    except asyncio.CancelledError:
        # This is expected when the session ends
        pass
    except Exception as e:
        print(f"Monitor Loop Error: {e}")

@cl.on_message
async def main(message: cl.Message):
    cmd = message.content.lower().strip()
    
    if cmd == "start":
        cl.user_session.set("running", True)
        await cl.Message(content="🛑 Attempting to launch Orchestrator...").send()
    
    elif cmd == "stop":
        cl.user_session.set("running", False)
        await cl.Message(content="🛑 Stopping all active agents...").send()
        
    elif cmd == "status":
        paths = cl.user_session.get("paths")
        tel_data = await get_telemetry_data(str(paths["telemetry"]))
        await cl.Message(content=f"Current Engine Status: **{tel_data['status']}**").send()
    
    else:
        await cl.Message(content=f"Unknown command: `{cmd}`. Try `start`, `stop`, or `status`.").send()
