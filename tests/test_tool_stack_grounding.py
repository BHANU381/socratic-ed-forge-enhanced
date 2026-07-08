import pytest
from unittest.mock import MagicMock, patch
from src.agents.core import GroundingFaithfulnessAuditor

def test_grounding_auditor_prompts_contain_tool_rules():
    # Assert that loading the grounding auditor prompt loads our updated Rule 4 and Rule 6
    auditor = GroundingFaithfulnessAuditor(theme="otto2_structured")
    
    # Mock self._run_with_retry to inspect the prompt passed to the agent
    with patch.object(auditor, "_run_with_retry", return_value='{"status": "APPROVED"}') as mock_run:
        auditor.audit_grounding(
            content="Using git to clone a repository.",
            course_context="CI/CD",
            module_context="Git basics",
            topic_context="Git workflow",
            tool_stack={"tools": ["GitHub"], "tech_stack": []},
            grounding_context={}
        )
        
        # Verify prompt details
        prompt = mock_run.call_args[0][0]
        assert "git" in prompt.lower()
        assert "github" in prompt.lower()
        assert "competitors" in prompt.lower()
        assert "brand names" in prompt.lower()


def test_grounding_auditor_failure_on_competitor_tools():
    # Assert that if the auditor parses a FAILED response for competitor tools, it correctly maps blockers
    auditor = GroundingFaithfulnessAuditor(theme="otto2_structured")
    
    mock_failed_response = """
    {
      "status": "FAILED",
      "blockers": [
        {
          "section": "Practical Walkthrough",
          "issue": "Draft mentions OpenAI ChatGPT which is a competitor to the required Gemini API in the tool stack.",
          "suggested_fix": "Replace references to OpenAI/ChatGPT with Gemini API."
        }
      ],
      "warnings": [],
      "notes": []
    }
    """
    
    with patch.object(auditor, "_run_with_retry", return_value=mock_failed_response):
        result = auditor.audit_grounding(
            content="Let's query OpenAI ChatGPT here.",
            course_context="AI loop",
            module_context="API integrations",
            topic_context="Calling models",
            tool_stack={"tools": ["Gemini API"], "tech_stack": []},
            grounding_context={}
        )
        
        assert result["status"] == "FAILED"
        assert len(result["blockers"]) == 1
        assert "OpenAI" in result["blockers"][0]["issue"]
        assert "Gemini" in result["blockers"][0]["suggested_fix"]
