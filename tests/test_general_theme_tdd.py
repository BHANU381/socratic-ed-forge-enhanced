import pytest
from unittest.mock import MagicMock
from src.agents.core import (
    ContentGenerator,
    Critic,
    Editor,
    Archivist,
    InternalLibrarian,
    Librarian,
    CurriculumJudgeEval
)

@pytest.fixture(autouse=True)
def mock_genai_client(monkeypatch):
    # Mock GEMINI_API_KEY env var
    monkeypatch.setenv("GEMINI_API_KEY", "fake_api_key")
    # Mock genai.Client to return a MagicMock
    mock_client = MagicMock()
    monkeypatch.setattr("google.genai.Client", lambda *args, **kwargs: mock_client)

def test_content_generator_generate():
    agent = ContentGenerator(role="Content Generator", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked content")
    
    result = agent.generate(
        module_title="Test Module",
        sub_title="Test Subtitle",
        content_context="Test Content Context",
        running_summary="Test Summary"
    )
    assert result == "mocked content"

def test_critic_critique():
    agent = Critic(role="Critic", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked critique")
    
    result = agent.critique(
        draft="Test Draft",
        content_context="Test Content Context"
    )
    assert result == "mocked critique"

def test_critic_critique_chat():
    agent = Critic(role="Critic", theme="general")
    agent._send_message_with_retry = MagicMock(return_value="mocked critique chat")
    mock_chat = MagicMock()
    
    result = agent.critique_chat(
        chat_session=mock_chat,
        draft="Test Draft",
        content_context="Test Content Context"
    )
    assert result == "mocked critique chat"

def test_editor_edit():
    agent = Editor(role="Editor", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked edit")
    
    result = agent.edit(
        draft="Test Draft",
        feedback="Test Feedback",
        sub_title="Test Subtitle",
        content_context="Test Content Context"
    )
    assert result == "mocked edit"

def test_editor_edit_chat():
    agent = Editor(role="Editor", theme="general")
    agent._send_message_with_retry = MagicMock(return_value="mocked edit chat")
    mock_chat = MagicMock()
    
    result = agent.edit_chat(
        chat_session=mock_chat,
        draft="Test Draft",
        feedback="Test Feedback",
        sub_title="Test Subtitle",
        content_context="Test Content Context"
    )
    assert result == "mocked edit chat"

def test_archivist_compress_submodule():
    agent = Archivist(role="Archivist", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked compression")
    
    result = agent.compress_submodule(
        content="Test Content"
    )
    assert result == "mocked compression"

def test_internal_librarian_audit_draft():
    agent = InternalLibrarian(role="Internal Librarian", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked audit draft")
    
    result = agent.audit_draft(
        content="Test Content"
    )
    assert result == "mocked audit draft"

def test_internal_librarian_repair():
    agent = InternalLibrarian(role="Internal Librarian", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked repair")
    
    # We call repair, passing typical mock parameters
    result = agent.repair(
        content="Test Content",
        repair_instructions="Fix formatting"
    )
    assert result == "mocked repair"

def test_librarian_audit_structure():
    agent = Librarian(role="Librarian", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked audit structure")
    
    result = agent.audit_structure(
        full_content="Test Full Content",
        content_context="Test Content Context"
    )
    assert result == "mocked audit structure"

def test_librarian_audit():
    agent = Librarian(role="Librarian", theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked audit")
    
    # We call audit, passing typical mock parameters
    result = agent.audit(
        full_content="Test Full Content"
    )
    assert result == "mocked audit"

def test_curriculum_judge_eval_evaluate():
    agent = CurriculumJudgeEval(theme="general")
    agent._run_with_retry = MagicMock(return_value="mocked evaluation result")
    
    result = agent.evaluate(
        course_name="Test Course Name",
        topic="Test Topic",
        duration_weeks=4,
        outline="Test Outline"
    )
    assert result == "mocked evaluation result"
    
    # Verify that the general prompt formats correctly and contains our outline
    called_prompt = agent._run_with_retry.call_args[0][0]
    assert "Test Outline" in called_prompt

