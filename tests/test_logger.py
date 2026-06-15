import pytest
import os
import json
from pathlib import Path
from src.utils.logger import log_event, update_status, update_telemetry, PROJECT_ROOT

def test_log_event(tmp_path, monkeypatch):
    # Mock PROJECT_ROOT so it writes to our temp directory instead of the real global logs
    monkeypatch.setattr("src.utils.logger.PROJECT_ROOT", tmp_path)
    
    session_dir = tmp_path / "test_session"
    session_dir.mkdir()
    
    log_event("TEST_ROLE", "This is a test message.", str(session_dir))
    
    # Verify global log
    global_log = tmp_path / "data" / "logs.txt"
    assert global_log.exists()
    assert "**TEST_ROLE**: This is a test message." in global_log.read_text()
    
    # Verify session log
    session_log = session_dir / "session_logs.txt"
    assert session_log.exists()
    assert "**TEST_ROLE**: This is a test message." in session_log.read_text()

def test_update_telemetry(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.logger.PROJECT_ROOT", tmp_path)
    
    telemetry_data = {"progress": 50, "status": "running"}
    update_telemetry(telemetry_data)
    
    global_telemetry = tmp_path / "data" / "telemetry.json"
    assert global_telemetry.exists()
    
    written_data = json.loads(global_telemetry.read_text())
    assert written_data["progress"] == 50
    assert "timestamp" in written_data

def test_log_event_no_session(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.logger.PROJECT_ROOT", tmp_path)
    
    log_event("TEST_ROLE", "Global message only", None)
    
    # Verify global log was created
    global_log = tmp_path / "data" / "logs.txt"
    assert global_log.exists()
    assert "Global message only" in global_log.read_text()
    
    # Ensure no session directory or log was created arbitrarily
    assert not (tmp_path / "session_logs.txt").exists()
