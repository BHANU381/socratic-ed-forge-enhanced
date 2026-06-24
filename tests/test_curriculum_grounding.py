import os
import json
import pytest
import datetime
from unittest.mock import MagicMock, patch
from src.agents.core import AgentBase, ContentGenerator
# from src.agents.core import Critic, Editor, FactChecker, Librarian
from src.engine.orchestrator import main, sanitize_headings, PROJECT_ROOT

# Requirement 1 & 7: Existing Experience Replay can still be loaded and generation loop runs when old Experience Replay data exists
@patch('src.agents.core.get_learned_lessons')
def test_experience_replay_loading(mock_get_lessons):
    mock_get_lessons.return_value = "Mocked lesson: do not fail syntax."
    agent = AgentBase("Test Role")
    context = agent._get_learning_context()
    assert context == "Mocked lesson: do not fail syntax."
    mock_get_lessons.assert_called_once()

# Requirement 2 & 3: content_context is included separately and appears before historical guidance
@patch('src.agents.core.get_learned_lessons')
def test_content_context_separately_and_ordered(mock_get_lessons):
    mock_get_lessons.return_value = "Avoid pandas append."
    gen = ContentGenerator("Generator")
    
    # Mock self._run_with_retry to inspect the prompt
    gen._run_with_retry = MagicMock(return_value="draft text")
    
    content_context = "Teach about Python dictionaries."
    gen.generate("Module 1", "Submodule 1", content_context)
    
    # Inspect prompt
    prompt = gen._run_with_retry.call_args[0][0]
    
    assert "### SITUATION & CONTEXT" in prompt
    assert "### HISTORICAL STYLE GUIDANCE" in prompt
    assert "Teach about Python dictionaries." in prompt
    
    idx_curriculum = prompt.find("### SITUATION & CONTEXT")
    idx_historical = prompt.find("### HISTORICAL STYLE GUIDANCE")
    
    assert idx_curriculum != -1
    assert idx_historical != -1
    assert idx_curriculum < idx_historical

# Requirement 4: Historical replay text cannot replace current submodule title or context
@patch('src.agents.core.get_learned_lessons')
def test_replay_cannot_replace_title_or_context(mock_get_lessons):
    # Mock replay text that attempts to spoof/overwrite
    mock_get_lessons.return_value = "Spoofed title: Fake title.\nSpoofed context: Fake context."
    gen = ContentGenerator("Generator")
    gen._run_with_retry = MagicMock(return_value="draft")
    
    sub_title = "Real Submodule Title"
    content_context = "Real Curriculum Context"
    
    gen.generate("Module 1", sub_title, content_context)
    prompt = gen._run_with_retry.call_args[0][0]
    
    # Verify real title and context are present in their correct places
    assert f"submodule '{sub_title}'" in prompt
    assert f"### SITUATION & CONTEXT\nCurriculum context to follow strictly:\n```\n{content_context}\n```" in prompt

# Requirement 5 & 6: System handles missing style_guide.json gracefully and instantiates a StyleSynthesizer Agent
# @patch('src.utils.learning_engine.migrate_old_lessons_if_needed')
# def test_style_guide_and_synthesizer_graceful(mock_migrate):
#     mock_migrate.return_value = None
#     # Verify style_guide.json missing doesn't crash the generator
#     style_guide_file = os.path.join(PROJECT_ROOT, 'data', 'learning_loop', 'style_guide.json')
#     if os.path.exists(style_guide_file):
#         try:
#             os.remove(style_guide_file)
#         except:
#             pass
#         
#     gen = ContentGenerator("Generator")
#     context = gen._get_learning_context()
#     assert context == ""
#     
#     # Check that StyleSynthesizer class exists
#     # from src.agents.core import StyleSynthesizer
#     # synthesizer = StyleSynthesizer()
#     # assert synthesizer.role == "style-synthesizer"

# Requirement 8: Missing Experience Replay data does not prevent lesson generation
@patch('src.agents.core.get_learned_lessons')
def test_missing_replay_data(mock_get_lessons):
    mock_get_lessons.return_value = ""
    gen = ContentGenerator("Generator")
    gen._run_with_retry = MagicMock(return_value="success draft")
    
    res = gen.generate("Module 1", "Submodule 1", "Some context")
    assert res == "success draft"
    
    prompt = gen._run_with_retry.call_args[0][0]
    assert "### HISTORICAL STYLE GUIDANCE" not in prompt



# Requirement 10: The _get_learning_context() boundary can later be replaced without changing Generator public interface
def test_learning_context_boundary_future_compatible():
    class CustomGenerator(ContentGenerator):
        def _get_learning_context(self) -> str:
            return "Synthesized Style-Guide: Ensure variable naming is snake_case."
            
    gen = CustomGenerator("CustomGen")
    gen._run_with_retry = MagicMock(return_value="draft")
    
    # Public interface signature: generate(module_title, sub_title, content_context)
    gen.generate("Module 1", "Submodule 1", "Curriculum instruction")
    
    prompt = gen._run_with_retry.call_args[0][0]
    assert "Synthesized Style-Guide: Ensure variable naming is snake_case." in prompt

# Additional check for Heading Duplication sanitization logic
def test_heading_sanitization():
    draft = "# Module 1: Introduction\n## Submodule: Python Basics\n### Introduction\nThis is content."
    required_headings = ["### Introduction", "### Core Concepts"]
    cleaned = sanitize_headings(draft, "Python Basics", required_headings)
    
    assert "# Module 1: Introduction" not in cleaned
    assert "## Submodule: Python Basics" not in cleaned
    assert "### Introduction" in cleaned
