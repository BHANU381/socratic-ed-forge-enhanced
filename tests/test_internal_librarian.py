import pytest
from unittest.mock import MagicMock
from src.agents.core import AgentBase

class MockInternalLibrarian(AgentBase):
    """A mock implementation of InternalLibrarian for testing purposes."""
    def __init__(self):
        super().__init__("Internal Librarian")
        self.client = MagicMock()

    def audit_draft(self, content):
        # Simulate the API call logic
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=content,
            config={"system_instruction": "You are a structural auditor."}
        )
        return response.text

def test_internal_librarian_detects_error():
    """Verify that the internal librarian identifies markdown formatting errors."""
    librarian = MockInternalLibrarian()
    
    # Mock the response to return a specific error message
    mock_response = MagicMock()
    mock_response.text = "- Remove level 2 heading\n- Close code block properly"
    librarian.client.models.generate_content.return_value = mock_response
    
    content = "## Broken Header\n```python\nprint('hello')"
    result = librarian.audit_draft(content)
    
    assert "Remove level 2 heading" in result
    assert "Close code block properly" in result
    assert librarian.client.models.generate_content.called

def test_internal_librarian_approves_correct_content():
    """Verify that the internal librarian approves properly formatted content."""
    librarian = MockInternalLibrarian()
    
    mock_response = MagicMock()
    mock_response.text = "APPROVED"
    librarian.client.models.generate_content.return_value = mock_response
    
    content = "### Valid Header\nThis is good content that is perfectly formatted."
    result = librarian.audit_draft(content)
    
    assert result == "APPROVED"
    assert librarian.client.models.generate_content.called
