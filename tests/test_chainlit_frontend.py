import os
import json
import glob
import pytest
from pathlib import Path

# Import functions from the actual app
# Note: In a real project, these would be in a utils.py, 
# but for this TDD cycle, we are importing directly from the app file.
from frontend.chainlit_app import get_telemetry_data, get_latest_book_path, resolve_project_paths

@pytest.mark.asyncio
async def test_get_telemetry_data_valid_json(tmp_path):
    """Test that valid JSON is parsed correctly with all required keys."""
    tel_file = tmp_path / "telemetry.json"
    data = {
        "status": "Running",
        "progress_percent": 45,
        "current_agent": "Generator",
        "total_tokens": 1000,
        "input_tokens": 400,
        "output_tokens": 600,
        "model_name": "gemini-1.5-flash",
        "current_module": "intro",
        "current_submodule": "supervised"
    }
    tel_file.write_text(json.dumps(data))
    
    result = await get_telemetry_data(str(tel_file))
    assert result["status"] == "Running"
    assert result["input_tokens"] == 400

@pytest.mark.asyncio
async def test_get_telemetry_data_missing_keys(tmp_path):
    """Test that missing keys are filled with defaults."""
    tel_file = tmp_path / "telemetry.json"
    data = {
        "status": "Idle",
        "progress_percent": 0,
        "current_agent": "None",
        "total_tokens": 0
    }
    tel_file.write_text(json.dumps(data))
    
    result = await get_telemetry_data(str(tel_file))
    assert result["input_tokens"] == 0
    assert result["model_name"] == "N/A"

@pytest.mark.asyncio
async def test_get_latest_book_path_finds_newest(tmp_path):
    """Test that the latest book is found based on modification time."""
    output_dir = tmp_path / "data" / "output"
    
    session1 = output_dir / "session_20260101"
    session2 = output_dir / "session_20260102"
    session1.mkdir(parents=True)
    session2.mkdir(parents=True)
    
    file1 = session1 / "old.md"
    file1.write_text("old")
    
    file2 = session2 / "new.md"
    file2.write_text("new")
    
    import time
    now = time.time()
    os.utime(str(file1), (now - 1000, now - 1000))
    os.utime(str(file2), (now, now))
    
    result = await get_latest_book_path(str(output_dir))
    assert str(file2) == result

def test_resolve_project_paths_correctly(tmp_path):
    """Test that paths are resolved correctly from a nested 'frontend' directory."""
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    app_file = frontend_dir / "app.py"
    app_file.write_text("")
    
    root, input_d, output_d, *extra = resolve_project_paths(str(app_file))
    
    assert root == tmp_path
    assert input_d == tmp_path / "data" / "input"
    assert output_d == tmp_path / "data" / "output"
