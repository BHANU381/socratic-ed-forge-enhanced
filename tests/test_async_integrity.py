import pytest
import asyncio
import os
import json
import glob
from pathlib import Path
import anyio

# Import functions from the actual app
from frontend.chainlit_app import get_telemetry_data, get_latest_book_path, resolve_project_paths

@pytest.mark.asyncio
async def test_get_telemetry_data_valid_json(tmp_path):
    """
    Verifies that get_telemetry_data works correctly with async I/O.
    """
    tel_file = tmp_path / "telemetry.json"
    data = {"status": "Running", "progress_percent": 50, "current_agent": "Generator"}
    tel_file.write_text(json.dumps(data))
    
    result = await get_telemetry_data(str(tel_file))
    assert result["status"] == "Running"
    assert result["progress_percent"] == 50
    assert result["current_agent"] == "Generator"

@pytest.mark.asyncio
async def test_get_telemetry_data_missing_keys(tmp_path):
    """
    Verifies that get_telemetry_data fills in missing keys with defaults.
    """
    tel_file = tmp_path / "telemetry.json"
    # Partial data
    data = {"status": "Running"}
    tel_file.write_text(json.dumps(data))
    
    result = await get_telemetry_data(str(tel_file))
    assert result["status"] == "Running"
    assert result["progress_percent"] == 0  # Default
    assert result["current_agent"] == "None"  # Default

@pytest.mark.asyncio
async def test_get_latest_book_path_finds_newest(tmp_path):
    """
    Verifies that get_latest_book_path works correctly with async I/O.
    """
    output_dir = tmp_path / "data" / "output"
    session1 = output_dir / "session_1"
    session2 = output_dir / "session_2"
    session1.mkdir(parents=True)
    session2.mkdir(parents=True)
    
    book1 = session1 / "old.md"
    book1.write_text("old")
    
    book2 = session2 / "new.md"
    book2.write_text("new")
    
    # Ensure book2 is newer
    import time
    time.sleep(0.1) 
    book2.touch()
    
    result = await get_latest_book_path(str(output_dir))
    assert str(book2) == result

@pytest.mark.asyncio
async def test_resolve_project_paths_correctly():
    """
    Verifies that resolve_project_paths returns expected absolute paths.
    """
    # We'll use the actual app file path for testing
    app_path = Path(__file__).parent.parent / "frontend" / "chainlit_app.py"
    root, input_d, output_d, tel_file, log_file = resolve_project_paths(str(app_path))
    
    assert Path(root).is_absolute()
    assert Path(input_d) == Path(root) / "data" / "input"
    assert Path(output_d) == Path(root) / "data" / "output"
