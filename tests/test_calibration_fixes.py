import pytest
from unittest.mock import MagicMock, patch
import json
from src.utils.patch_utils import apply_section_patch
from src.utils.learning_engine import record_lesson, get_learned_lessons, clear_style_guide

# =====================================================================
# Test Group D: Patch editor heading matching
# =====================================================================

def test_patch_editor_heading_matching():
    draft = """### Hook: The transition from manual coding to AI-native orchestration is here.
This is the hook details.

#### Core Idea
This is the core idea explaining things.

#### Implementation
This is the implementation detail.

#### Why it Matters
This is why it matters.
"""
    
    # 1. Patch Hook (with colon and sentence)
    res = apply_section_patch(draft, "Hook", "New hook content")
    assert "New hook content" in res
    # Heading format should be preserved or normalized cleanly
    assert "### Hook" in res or "### Hook:" in res

    # 2. Patch Hook:
    res = apply_section_patch(draft, "Hook:", "Another hook content")
    assert "Another hook content" in res

    # 3. Patch Hook with full text
    res = apply_section_patch(draft, "Hook: The transition from manual coding to AI-native orchestration is here.", "Cleaned hook")
    assert "Cleaned hook" in res

    # 4. Patch Core Idea
    res = apply_section_patch(draft, "Core Idea", "New core idea")
    assert "New core idea" in res

    # 5. Patch Implementation
    res = apply_section_patch(draft, "Implementation", "New implementation")
    assert "New implementation" in res

    # 6. Patch Why it Matters
    res = apply_section_patch(draft, "Why it Matters", "New why it matters")
    assert "New why it matters" in res


# =====================================================================
# Test Group E: LearningEngine filtering
# =====================================================================

def test_learning_engine_filtering(tmp_path, monkeypatch):
    import src.utils.learning_engine as le
    temp_style_guide = tmp_path / "style_guide_test.json"
    monkeypatch.setattr(le, "STYLE_GUIDE_FILE", str(temp_style_guide))
    
    # Ensure starting empty
    temp_style_guide.write_text('{"rules": []}', encoding="utf-8")
    
    # 1. Do not learn from word-count complaints
    record_lesson("Module 1", "Submodule 1", "Core Idea has only 200 words, but should be 600 words", "content")
    # 2. Do not learn from 30-40 minute lesson complaints
    record_lesson("Module 1", "Submodule 2", "The lesson fails to represent 30-40 minute lesson depth", "content")
    # 3. Do not learn from heading structure complaints when deterministic passed
    record_lesson("Module 1", "Submodule 3", "Heading hierarchy nested incorrectly after deterministic pass", "content")
    
    with open(temp_style_guide, "r") as f:
        data = json.load(f)
    assert len(data.get("rules", [])) == 0, "Noisy rules should be filtered and not learned"
    
    # 4. DO learn from repeated real content issues
    # Note: We trigger rule recording by recording it twice to simulate repeated pattern detection in orchestrator
    # If the rule is not noisy, it should be processed. Since StyleSynthesizer is mocked in tests, we mock it.
    with patch("src.agents.core.StyleSynthesizer") as mock_synth_cls:
        mock_instance = mock_synth_cls.return_value
        mock_instance.synthesize_rule.return_value = "Ensure Implementation contains practical examples."
        mock_instance.find_duplicate_rule.return_value = "NEW"
        
        record_lesson("Module 1", "Submodule 4", "Implementation repeats theory instead of giving practical application", "content")
        
        with open(temp_style_guide, "r") as f:
            data_new = json.load(f)
        assert len(data_new.get("rules", [])) > 0, "Should learn real pedagogical rules"


# =====================================================================
# Test Groups A, B, and C: Semantic Evaluator calibration & behavior
# =====================================================================

def test_otto2_semantic_evaluator_prompt_boundaries():
    from src.utils.prompt_loader import load_prompt
    
    dummy_kwargs = {
        "course_topic": "AI-Native Software Engineering",
        "submodule_title": "1.1 Workspace Setup",
        "learner_level": "Beginner",
        "code_example_style": "Progressive Prod",
        "explanation_depth": "Deep",
        "module_position": "1/4",
        "lesson_contract": "lesson contract mockup",
        "running_summary": "running summary details",
        "breakdown": "breakdown details",
        "topic_constraints": "constraints details",
        "action_items": "- Action item 1",
        "common_mistakes": "- Common mistake 1",
        "expert_heuristic": "heuristic details",
        "evaluation_path": "path details",
        "draft": "draft content"
    }
    
    prompt_text, _ = load_prompt("semantic_evaluator.md", theme="otto2", **dummy_kwargs)
    prompt_lower = prompt_text.lower()
    
    # Assert Group A: Theme-aware boundaries (should not require default elements or length limits)
    assert "active lesson contract is the absolute source of truth" in prompt_lower
    assert "do not require" in prompt_lower
    assert "introduction" in prompt_lower
    assert "summary and bridge" in prompt_lower
    assert "guided explanation" in prompt_lower
    assert "600-word" in prompt_lower
    
    # Assert Group B: Real semantic blockers
    assert "block only if" in prompt_lower
    assert "off-topic" in prompt_lower
    
    # Assert Group C: Deterministic/semantic separation
    assert "deterministic validation has passed" in prompt_lower
    assert "do not create a semantic blocker for heading hierarchy" in prompt_lower
    assert "warn only if" in prompt_lower


# =====================================================================
# Phase 2: Target Words, Placeholders, and Contract Semantics
# =====================================================================

def test_contract_target_words_loading_and_fallback():
    from src.models.schemas import SectionRequirement
    # 1. Loads with target_words
    sec = SectionRequirement(title="Core Idea", min_words=180, target_words=600)
    assert sec.target_words == 600
    
    # 2. Backward compatible default (None)
    sec_legacy = SectionRequirement(title="Core Idea", min_words=180)
    assert sec_legacy.target_words is None


def test_deterministic_validator_target_words():
    from src.models.schemas import LessonContract, SectionRequirement
    from src.validators.lesson_contract_validator import validate_lesson_contract
    
    contract = LessonContract(
        lesson_contract_name="test_target_words",
        sections=[
            SectionRequirement(title="Core Idea", min_words=180, target_words=600, required=True, required_level=4)
        ]
    )
    
    # 3. Core Idea with 250 words passes min_words=180 and warns below target_words=600
    draft_250 = "#### Core Idea\n" + "word " * 250
    res_250 = validate_lesson_contract(draft_250, contract)
    assert res_250.passed is True
    assert any(i.severity == "warning" and "target" in i.message.lower() for i in res_250.issues)
    
    # 4. Core Idea with 650 words passes with no target warning
    draft_650 = "#### Core Idea\n" + "word " * 650
    res_650 = validate_lesson_contract(draft_650, contract)
    assert res_650.passed is True
    assert not any("target" in i.message.lower() for i in res_650.issues)
    
    # 5. Core Idea with 50 words fails when below min_words and not useful (no code blocks or markdown lists)
    draft_50 = "#### Core Idea\n" + "word " * 50
    res_50 = validate_lesson_contract(draft_50, contract)
    assert res_50.passed is False
    assert any(i.severity == "blocker" and "below the minimum" in i.message.lower() for i in res_50.issues)
    
    # 6. Implementation below target_words but containing useful elements (e.g. code block) passes with warning
    contract_impl = LessonContract(
        lesson_contract_name="test_impl",
        sections=[
            SectionRequirement(title="Implementation", min_words=180, target_words=600, required=True, required_level=4)
        ]
    )
    draft_impl_100_useful = "#### Implementation\nSome prose text here.\n```python\nprint('hello')\n```\n" + "word " * 100
    res_impl = validate_lesson_contract(draft_impl_100_useful, contract_impl)
    # The word count is 100 + code, which is below min_words=180, but since code fence is present, it is useful!
    # Under new rules: below min_words but useful should be a warning only.
    assert res_impl.passed is True
    assert any(i.severity == "warning" for i in res_impl.issues)


def test_placeholder_validation_exemptions():
    from src.validators.markdown_validator import validate_markdown_structure
    
    # 1. [Code Snippet] inside an instructional prompt example or template is allowed (warning instead of blocker)
    instructional_content = """### Hook
This is a hook.

#### Core Idea
Here is the instructional template:
> To write this code, use [Code Snippet] placeholder.
"""
    res1 = validate_markdown_structure(instructional_content)
    assert not any(i.severity == "blocker" and "placeholder" in i.issue_type.lower() for i in res1.issues)
    
    # 2. [Insert Code] inside debugging instructions/comments is allowed
    comment_content = """### Hook
This is a hook.

#### Core Idea
When debugging, check this snippet:
```python
# [Insert Code] here
```
"""
    res2 = validate_markdown_structure(comment_content)
    assert not any(i.severity == "blocker" and "placeholder" in i.issue_type.lower() for i in res2.issues)
    
    # 3. Unresolved standalone [Insert Code Here] still fails as a blocker
    unresolved_content = """### Hook
This is a hook.

#### Core Idea
To run the web server:
[Insert Code Here]
"""
    res3 = validate_markdown_structure(unresolved_content)
    assert any(i.severity == "blocker" and "placeholder" in i.issue_type.lower() for i in res3.issues)

