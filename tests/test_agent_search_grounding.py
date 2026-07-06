from unittest.mock import MagicMock, patch
import pytest
from src.agents.core import AgentBase, PatchEditor
from src.utils.search_client import search_duckduckgo

def test_agent_base_never_uses_native_google_search_grounding():
    with patch("src.agents.core.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        agent = AgentBase(role="Content Generator")
        agent.client = mock_client
        agent._run_with_retry("test prompt", enable_google_search=True)
        _, kwargs = mock_client.models.generate_content.call_args
        # We assert that "tools" is NOT registered on the Gemini model config anymore
        assert "tools" not in kwargs.get("config", {})

def test_search_duckduckgo_utility():
    with patch("src.utils.search_client.DDGS") as mock_ddgs_cls:
        mock_ddgs = MagicMock()
        mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs
        mock_ddgs.text.return_value = [
            {"title": "Linux Networking Basics", "href": "https://linux.org/net", "body": "Learn route commands, DNS lookup details."}
        ]
        res = search_duckduckgo("Linux Basics")
        assert "Linux Networking Basics" in res
        assert "https://linux.org/net" in res
        assert "Learn route commands" in res

def test_orchestrator_integrates_duckduckgo_results():
    from src.engine.orchestrator import Orchestrator
    from src.models.schemas import CourseStructure
    
    course_data = {
        "course_title": "Python Core",
        "course_context": "Core Python concepts",
        "modules": [],
        "enable_google_search": True
    }
    course = CourseStructure.model_validate(course_data)
    from pathlib import Path
    with patch("src.engine.orchestrator.search_duckduckgo") as mock_search, \
         patch("src.engine.orchestrator.ContentGenerator") as mock_gen_cls:
        
        mock_search.return_value = "DuckDuckGo search context info"
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        
        pipeline = Orchestrator(course=course, session_dir=Path("data/sessions/test"))
        pipeline.generator = mock_gen
        
        # Triggering generate draft should call search_duckduckgo
        submodule = MagicMock(title="Networking")
        with patch.object(pipeline.generator, "generate") as mock_generate:
            mock_generate.return_value = "### Networking\nDraft Content"
            pipeline.run_submodule_pipeline(submodule, "Module Title", "Content Context", "Learning Context")
            mock_search.assert_called_once_with("Networking Core Python concepts")
            _, kwargs = mock_generate.call_args
            assert "DuckDuckGo search context info" in kwargs.get("grounding_context", "")
