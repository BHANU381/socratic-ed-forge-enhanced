import pytest
from fastapi.testclient import TestClient
import json
from backend.server import app

client = TestClient(app)

def test_approve_endpoint(tmp_path, monkeypatch):
    # Mock OUTPUT_DIR
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    session_id = "session_test_approve"
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    
    pause_file = session_dir / "module_pause.json"
    pause_data = {
        "status": "paused_for_review",
        "module_index": 0,
        "module_title": "Module 1"
    }
    with open(pause_file, "w", encoding="utf-8") as f:
        json.dump(pause_data, f)
        
    response = client.post(
        "/api/session/approve",
        json={"session_id": session_id}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "approved"}
    
    # The pause file status should be updated to approved
    with open(pause_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "approved"


def test_edit_selection_endpoint(tmp_path, monkeypatch):
    # Mock OUTPUT_DIR
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    # Create mock session dir and initial manifest
    session_id = "session_123"
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    manifest_file = session_dir / "run_manifest.json"
    import json
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_tokens": 100,
            "agent_tokens": {
                "patch_editor": 10
            }
        }, f)
        
    from src.models.schemas import PatchResult
    mock_result = PatchResult(
        operation="replace_section",
        target_heading="#### Persona Analogies",
        replacement_markdown="Patched text block",
        reason="test reason"
    )
    
    # Mock PatchEditor using a helper class to simulate token tracking attributes
    class MockPatchEditor:
        def __init__(self, *args, **kwargs):
            self.input_tokens = 50
            self.output_tokens = 20
        def edit_patch(self, *args, **kwargs):
            return mock_result

    monkeypatch.setattr("src.agents.core.PatchEditor", MockPatchEditor)
    
    response = client.post(
        "/api/session/edit/selection",
        json={
            "session_id": session_id,
            "selection_text": "Original text block",
            "full_text": "Introduction\n\nOriginal text block\n\nConclusion",
            "scope": "selection",
            "instruction": "Change text to patched",
            "theme": "default"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["patched_text"] == "Patched text block"
    
    # Assert that the manifest token counts have been updated in the session directory
    with open(manifest_file, "r", encoding="utf-8") as f:
        updated_data = json.load(f)
    assert updated_data["total_tokens"] == 170
    assert updated_data["agent_tokens"]["patch_editor"] == 80


def test_chat_endpoint(tmp_path, monkeypatch):
    # Mock core chat completion
    from src.agents.core import AgentBase
    monkeypatch.setattr(AgentBase, "_run_with_retry", lambda self, prompt: "Reviewer response text")
    
    # Mock OUTPUT_DIR
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    response = client.post(
        "/api/session/chat",
        json={
            "session_id": "session_123",
            "message": "Can you check this section?",
            "submodule_filename": "submodule_1_1.md"
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {"response": "Reviewer response text"}


def test_edit_triggers_recompile(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("backend.server.INPUT_DIR", tmp_path)
    
    course_input = tmp_path / "course_input.json"
    import json
    with open(course_input, "w", encoding="utf-8") as f:
        json.dump({
            "course_name": "Enterprise Test",
            "topic": "testing context",
            "duration_weeks": 2,
            "modules": [
                {
                    "title": "Module 1",
                    "module_context": "M1 context",
                    "submodules": [
                        {"title": "Sub 1.1", "content_context": "sub context"}
                    ]
                }
            ]
        }, f)
        
    session_id = "session_edit_compile"
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    
    response = client.post(
        "/api/sessions/edit",
        json={
            "session_id": session_id,
            "submodule_filename": "submodule_1_1.md",
            "content": "Edited submodule content"
        }
    )
    
    assert response.status_code == 200
    master_file = session_dir / "Enterprise_Test.md"
    assert master_file.exists()
    assert "Edited submodule content" in master_file.read_text(encoding="utf-8")


def test_server_lifespan_teardown(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.server.PID_FILE", tmp_path / "runner.pid")
    monkeypatch.setattr("backend.server.STOP_FLAG", tmp_path / "stop.flag")
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    (tmp_path / "runner.pid").write_text("999999")
    
    monkeypatch.setattr("backend.server._is_running", lambda pid: True)
    
    from unittest.mock import MagicMock
    mock_kill = MagicMock()
    monkeypatch.setattr("backend.server._kill_process_tree", mock_kill)
    
    with TestClient(app) as client:
        pass
        
    mock_kill.assert_called_once_with(999999)


def test_edit_selection_context_enrichment(tmp_path, monkeypatch):
    # Mock OUTPUT_DIR and a custom PROMPTS_DIR
    monkeypatch.setattr("backend.server.OUTPUT_DIR", tmp_path)
    
    # Create mock session dir and run_manifest.json (with theme defined)
    session_id = "session_context_999"
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    manifest_file = session_dir / "run_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({
            "prompt_theme": "otto2_structured",
            "total_tokens": 0
        }, f)
        
    # Create a mock prompts structure
    prompts_dir = tmp_path / "prompts"
    theme_dir = prompts_dir / "otto2_structured"
    theme_dir.mkdir(parents=True)
    prompt_file = theme_dir / "content_generator.md"
    
    # Write mock generator prompt instructions with sections
    prompt_file.write_text(
        "### TEMPLATE / FORMAT\n\n"
        "#### Core Idea\n"
        "- First rule of core idea.\n"
        "- Second rule of core idea.\n\n"
        "#### Edge Cases\n"
        "- First edge case directive.\n"
        "- Second edge case directive.\n\n"
        "#### Common Mistakes\n"
        "- Avoid mistakes.\n",
        encoding="utf-8"
    )
    monkeypatch.setattr("backend.server.PROMPTS_DIR", prompts_dir)

    # We mock PatchEditor to inspect what arguments edit_patch receives
    received_args = {}
    class InspectingPatchEditor:
        def __init__(self, *args, **kwargs):
            self.input_tokens = 5
            self.output_tokens = 5
        def edit_patch(self, **kwargs):
            nonlocal received_args
            received_args = kwargs
            from src.models.schemas import PatchResult
            return PatchResult(
                operation="replace_section",
                target_heading="#### Edge Cases",
                replacement_markdown="Patched mock results",
                reason="success mock"
            )

    monkeypatch.setattr("src.agents.core.PatchEditor", InspectingPatchEditor)

    # Post selection request crossing two sections
    response = client.post(
        "/api/session/edit/selection",
        json={
            "session_id": session_id,
            "selection_text": "text selection\n\n#### Edge Cases\nmore",
            "full_text": "#### Core Idea\ntext selection\n\n#### Edge Cases\nmore text",
            "scope": "selection",
            "instruction": "Expand context",
            "theme": "otto2_structured"
        }
    )

    assert response.status_code == 200
    # The heading argument passed to edit_patch should be the compound heading showing crossed sections
    assert "Core Idea" in received_args.get("heading", "")
    assert "Edge Cases" in received_args.get("heading", "")
    # The grounding_context should contain both parsed rules from the template md
    assert "First rule of core idea." in received_args.get("grounding_context", "")
    assert "First edge case directive." in received_args.get("grounding_context", "")




