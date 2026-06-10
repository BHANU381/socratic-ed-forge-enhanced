import pytest
from unittest.mock import MagicMock
from src.agents.core import AgentBase

class MockFactChecker(AgentBase):
    """A mock implementation of a FactChecker for testing purposes."""
    def __init__(self):
        super().__init__("Fact-Checker")
        self.client = MagicMock()

    def check_facts(self, content):
        # Simulate the API call logic
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=content,
            config={"system_instruction": "You are a fact checker."}
        )
        return response.text

def test_fact_checker_detects_error():
    """Verify that the fact checker identifies a technical hallucination."""
    checker = MockFactChecker()
    
    # Mock the response to return a specific error message
    mock_response = MagicMock()
    mock_response.text = "ERROR: The statement 'Python is a compiled language' is technically incorrect. Python is an interpreted language."
    checker.client.models.generate_content.return_value = mock_response
    
    content = "Python is a compiled language."
    result = checker.check_facts(content)
    
    assert "ERROR" in result
    assert "interpreted language" in result
    assert checker.client.models.generate_content.called

def test_fact_checker_approves_correct_content():
    """Verify that the fact checker approves correct content."""
    checker = MockFactChecker()
    
    mock_response = MagicMock()
    mock_response.text = "APPROVED"
    checker.client.models.generate_content.return_value = mock_response
    
    content = "Python is an interpreted language."
    result = checker.check_facts(content)
    
    assert result == "APPROVED"
    assert checker.client.models.generate_content.called
