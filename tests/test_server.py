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


def test_start_pipeline_with_custom_controls(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.server.INPUT_DIR", tmp_path)
    monkeypatch.setattr("backend.server._get_pid", lambda: None)
    
    valid_data = {
        "course_name": "Test Custom",
        "topic": "Testing Custom Controls",
        "duration_weeks": 2,
        "modules": []
    }
    
    from unittest.mock import MagicMock
    mock_proc = MagicMock()
    mock_proc.pid = 98765
    captured_env = {}
    
    def mock_popen(args, env, **kwargs):
        nonlocal captured_env
        captured_env = env
        return mock_proc
        
    monkeypatch.setattr("backend.server.subprocess.Popen", mock_popen)
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", json.dumps(valid_data).encode("utf-8"), "application/json")},
        data={
            "learner_level": "advanced",
            "code_example_style": "minimal",
            "explanation_depth": "deep",
            "quality_profile": "textbook",
            "resume": "true"
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "started", "pid": 98765}
    
    # Verify written file content contains custom parameters
    written_file = tmp_path / "course_input.json"
    assert written_file.exists()
    written_data = json.loads(written_file.read_text())
    assert written_data["learner_level"] == "advanced"
    assert written_data["code_example_style"] == "minimal"
    assert written_data["explanation_depth"] == "deep"
    assert written_data["quality_profile"] == "textbook"
    
    # Verify RUN_TYPE env is passed as resume_existing_run
    assert captured_env.get("RUN_TYPE") == "resume_existing_run"


def test_api_sessions_list(tmp_path, monkeypatch):
    # Mock OUTPUT_DIR in backend.server to use tmp_path
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    # Create a dummy session folder with a manifest
    session_dir = tmp_path / "session_20260707_160810"
    session_dir.mkdir()
    manifest_file = session_dir / "run_manifest.json"
    manifest_data = {
        "course_name": "Enterprise AI",
        "prompt_theme": "otto2_structured",
        "completion_rate": 85
    }
    manifest_file.write_text(json.dumps(manifest_data))
    
    response = client.get("/api/sessions")
    assert response.status_code == 200
    sessions = response.json().get("sessions", [])
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session_20260707_160810"
    assert sessions[0]["metadata"]["course_name"] == "Enterprise AI"


def test_api_sessions_edit(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    session_dir = tmp_path / "session_20260707_160810"
    session_dir.mkdir()
    
    submodule_file = session_dir / "submodule_1_1.md"
    submodule_file.write_text("Original Draft Content")
    
    edit_payload = {
        "session_id": "session_20260707_160810",
        "submodule_filename": "submodule_1_1.md",
        "content": "Edited Draft Content"
    }
    
    response = client.post("/api/sessions/edit", json=edit_payload)
    assert response.status_code == 200
    assert response.json().get("status") == "updated"
    assert submodule_file.read_text() == "Edited Draft Content"


def test_api_sessions_preview(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    session_dir = tmp_path / "session_20260707_160810"
    session_dir.mkdir()
    
    textbook_file = session_dir / "Enterprise_AI.md"
    textbook_file.write_text("Full Textbook Markdown Content", encoding="utf-8")
    
    response = client.get("/api/sessions/session_20260707_160810/preview")
    assert response.status_code == 200
    assert response.json().get("filename") == "Enterprise_AI.md"
    assert response.json().get("content") == "Full Textbook Markdown Content"


def test_start_pipeline_with_custom_session_name(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.server.INPUT_DIR", tmp_path)
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("backend.server._get_pid", lambda: None)
    
    valid_data = {
        "course_name": "Test Naming",
        "topic": "Testing Custom Session Name",
        "duration_weeks": 2,
        "modules": []
    }
    
    from unittest.mock import MagicMock
    mock_proc = MagicMock()
    mock_proc.pid = 44444
    captured_env = {}
    
    def mock_popen(args, env, **kwargs):
        nonlocal captured_env
        captured_env = env
        return mock_proc
        
    monkeypatch.setattr("backend.server.subprocess.Popen", mock_popen)
    
    response = client.post(
        "/api/start",
        files={"file": ("course_input.json", json.dumps(valid_data).encode("utf-8"), "application/json")},
        data={
            "resume": "false",
            "session_name": "Super Custom Session Name 123"
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "started", "pid": 44444}
    
    # Verify a session directory was pre-created and populated
    session_id = captured_env.get("SESSION_ID")
    assert session_id is not None
    assert session_id.startswith("session_")
    
    session_dir = tmp_path / session_id
    assert session_dir.exists()
    
    # Verify course_input.json was written to the session directory
    course_input = session_dir / "course_input.json"
    assert course_input.exists()
    
    # Verify run_manifest.json contains the custom session name
    manifest_file = session_dir / "run_manifest.json"
    assert manifest_file.exists()
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["session_name"] == "Super Custom Session Name 123"
    assert manifest_data["status"] == "Running"


