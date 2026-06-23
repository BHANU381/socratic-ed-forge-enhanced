import os
import time
import random
import pytest
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load env variables
load_dotenv()

class MockAgent:
    """A simple mock class to test the retry logic without needing the real API."""
    def __init__(self, role):
        self.role = role
        self.call_count = 0

    def _run_with_retry(self, prompt):
        retries = 0
        base_backoff = 0.01 
        while retries < 5:
            try:
                self.call_count += 1
                # Simulate a 503 error on the first two attempts
                if self.call_count < 3:
                    raise Exception("503 UNAVAILABLE: Server Busy")
                return "success"
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "429" in error_str or "500" in error_str:
                    retries += 1
                    time.sleep(base_backoff)
                else:
                    raise e
        return "failed"

def test_retry_logic_on_api_error():
    """Verify that the agent retries when a 503 error occurs."""
    agent = MockAgent("Mock")
    result = agent._run_with_retry("test prompt")
    
    assert result == "success"
    assert agent.call_count == 3

def test_agent_initialization_logic():
    """Basic check to ensure role and setup works."""
    from src.agents.core import ContentGenerator
    gen = ContentGenerator("Test Generator")
    assert gen.role == "Test Generator"

def test_semantic_evaluator_agent():
    """Test that SemanticEvaluator parses mock API output correctly and handles errors."""
    from src.agents.core import SemanticEvaluator
    from src.models.schemas import ValidationResult
    
    evaluator = SemanticEvaluator()
    assert evaluator.role == "semantic-evaluator"
    assert evaluator.response_schema == ValidationResult
    
    # Mock self._run_with_retry to simulate successful evaluator feedback
    evaluator._run_with_retry = MagicMock(return_value='{"passed": true, "issues": []}')
    
    res = evaluator.evaluate(
        draft="Some draft",
        lesson_contract="Some contract",
        course_topic="Python",
        submodule_title="Variables"
    )
    assert isinstance(res, ValidationResult)
    assert res.passed
    assert len(res.issues) == 0
    
    # Mock error case (invalid JSON)
    evaluator._run_with_retry = MagicMock(return_value='Invalid JSON!')
    res = evaluator.evaluate(
        draft="Some draft",
        lesson_contract="Some contract",
        course_topic="Python",
        submodule_title="Variables"
    )
    assert isinstance(res, ValidationResult)
    assert not res.passed
    assert len(res.issues) == 1
    assert res.issues[0].issue_type == "json_parse_error"

def test_patch_editor_agent():
    """Test that PatchEditor passes parameters correctly and returns output."""
    from src.agents.core import PatchEditor
    
    editor = PatchEditor()
    assert editor.role == "patch-editor"
    
    editor._run_with_retry = MagicMock(return_value='{"operation": "replace_section", "target_heading": "Introduction", "replacement_markdown": "New patched content", "reason": "Fixed"}')
    res = editor.edit_patch(
        draft="Old content",
        feedback="Missing stuff",
        heading="Introduction",
        course_topic="Python",
        submodule_title="Variables"
    )
    from src.models.schemas import PatchResult
    assert isinstance(res, PatchResult)
    assert res.replacement_markdown == "New patched content"

