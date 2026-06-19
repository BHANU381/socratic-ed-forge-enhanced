import pytest
from fastapi.testclient import TestClient
import json
from backend.server import app, INPUT_DIR

client = TestClient(app)

def test_start_pipeline_valid_schema(tmp_path, monkeypatch):
    # Mock INPUT_DIR to use temp path
    monkeypatch.setattr("backend.server.INPUT_DIR", tmp_path)
    
    valid_data = {
        "course_name": "Test",
        "topic": "Testing",
        "duration_weeks": 4,
        "modules": []
    }
    
    # We will just test the validation part, so we mock _get_pid and subprocess.Popen
    monkeypatch.setattr("backend.server._get_pid", lambda: None)
    
    from unittest.mock import MagicMock
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    monkeypatch.setattr("backend.server.subprocess.Popen", lambda *args, **kwargs: mock_proc)
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", json.dumps(valid_data).encode("utf-8"), "application/json")}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "started", "pid": 12345}
    
    # Verify file was written
    written_file = tmp_path / "course_input.json"
    assert written_file.exists()
    assert json.loads(written_file.read_text()) == valid_data

def test_start_pipeline_invalid_schema(monkeypatch):
    monkeypatch.setattr("backend.server._get_pid", lambda: None)
    
    # Missing required fields like course_name
    invalid_data = {
        "topic": "Testing"
    }
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", json.dumps(invalid_data).encode("utf-8"), "application/json")}
    )
    
    # We expect a 422 Unprocessable Entity due to Pydantic ValidationError
    assert response.status_code == 422
    assert "Schema Validation Failed" in response.json()["detail"]

def test_start_pipeline_malformed_json(monkeypatch):
    monkeypatch.setattr("backend.server._get_pid", lambda: None)
    
    # Intentionally malformed JSON string (missing closing brace)
    malformed_json = '{"course_name": "Test", "topic": "Testing"'
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", malformed_json.encode("utf-8"), "application/json")}
    )
    
    # We expect a 400 Bad Request due to JSONDecodeError
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]

def test_start_pipeline_already_running(monkeypatch):
    # Simulate an already running pipeline
    monkeypatch.setattr("backend.server._get_pid", lambda: 9999)
    monkeypatch.setattr("backend.server._is_running", lambda pid: True)
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", b"{}", "application/json")}
    )
    
    # We expect a 409 Conflict
    assert response.status_code == 409
    assert "Pipeline already running" in response.json()["detail"]

def test_api_prompt_themes_returns_directories():
    response = client.get("/api/prompt-themes")
    assert response.status_code == 200
    data = response.json()
    assert "themes" in data
    assert isinstance(data["themes"], list)

def test_api_start_rejects_invalid_theme_name(monkeypatch):
    monkeypatch.setattr("backend.server._get_pid", lambda: None)
    
    invalid_data = {
        "course_name": "Test",
        "topic": "Testing",
        "duration_weeks": 4,
        "modules": [],
        "prompt_theme": "../../../etc" # Invalid path traversal
    }
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", json.dumps(invalid_data).encode("utf-8"), "application/json")}
    )
    
    # We expect a 422 Unprocessable Entity due to Pydantic regex validation on prompt_theme
    assert response.status_code == 422
    assert "Schema Validation Failed" in response.json()["detail"]

