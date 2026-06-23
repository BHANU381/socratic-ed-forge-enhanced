import pytest
from src.models.schemas import LessonContract, SectionRequirement, HeadingRules, HeadingRuleMainContent
from src.validators.markdown_validator import validate_markdown_structure
from src.validators.lesson_contract_validator import validate_lesson_contract

def test_markdown_validator_unclosed_code_fence():
    # Unclosed code fence should trigger a blocker issue
    content = """# Section 1
Here is some code:
```python
print("Hello world")
No closing fence here!
"""
    result = validate_markdown_structure(content)
    assert not result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) >= 1
    assert any("unclosed code fence" in i.message.lower() for i in blockers)

def test_markdown_validator_placeholders():
    # Leftover TODOs or placeholders should trigger blocker/warning
    content = """# Introduction
This is a [TODO: add more details] section.
TODO: write this.
We should check for [Insert image here] too.
"""
    result = validate_markdown_structure(content)
    assert not result.passed
    issues = result.issues
    assert len(issues) >= 3
    assert any("todo" in i.message.lower() for i in issues)
    assert any("placeholder" in i.message.lower() for i in issues)

def test_markdown_validator_placeholder_context():
    # Placeholders inside code blocks or explicit template instructions should not be blockers
    content = """# Introduction
This is a standard [TODO: fix this] which should be a blocker.

Here is an example template:
[Insert User Name Here]

```json
{
  "prompt": "[Insert topic]"
}
```
"""
    result = validate_markdown_structure(content)
    
    # We should have exactly 1 blocker (the first TODO) and 0 blockers for the code block or template.
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) == 1
    assert "todo" in blockers[0].message.lower()
    
    # The others should either be warnings or not flagged at all
    warnings = [i for i in result.issues if i.severity == "warning"]
    assert any("insert" in w.message.lower() for w in warnings) or len(warnings) == 0

def test_markdown_validator_happy_path():
    content = """# Introduction
This is a clean markdown file.
```python
print("Hello world")
```
It has proper headers and structure.
"""
    result = validate_markdown_structure(content)
    assert result.passed
    assert len(result.issues) == 0
    assert "Introduction" in result.detected_headings

def test_markdown_validator_ignores_fenced_code_comments():
    content = """# Introduction
Some intro text.
```python
# Step 1: The comment inside code
print("Hello")
### Not a real heading
```
# Real Section
End
"""
    result = validate_markdown_structure(content)
    # The current buggy behavior would treat '# Step 1' as a heading and flag it as an empty section.
    assert result.passed
    issues = result.issues
    assert len([i for i in issues if i.issue_type == "empty_section"]) == 0
    assert "Step 1: The comment inside code" not in result.detected_headings
    assert "Not a real heading" not in result.detected_headings


def test_lesson_contract_validator_missing_required():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Introduction", aliases=["Intro", "Getting Started"], required=True),
            SectionRequirement(title="Exercises", required=True),
            SectionRequirement(title="Summary", required=False)
        ]
    )
    # Exercises heading is missing here
    content = """# Intro
Welcome to the course.
# Summary
Here is a summary.
"""
    result = validate_lesson_contract(content, contract)
    assert not result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) == 1
    assert blockers[0].section == "Exercises"
    assert "missing" in blockers[0].message.lower()

def test_lesson_contract_validator_word_count():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Detailed Guide", min_words=20, required=True)
        ]
    )
    # "Too short" is only 2 words, which is less than 20
    content = """# Detailed Guide
Too short.
"""
    result = validate_lesson_contract(content, contract)
    assert not result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) == 1
    assert blockers[0].section == "Detailed Guide"
    assert "word count" in blockers[0].message.lower()

def test_lesson_contract_validator_word_count_near_miss():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Detailed Guide", min_words=100, required=True)
        ]
    )
    # The minimum is 100, 50% is 50. 
    # If the text has 60 words, it should be a warning, not a blocker.
    content = "# Detailed Guide\n" + " word" * 60
    result = validate_lesson_contract(content, contract)
    assert result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) == 0
    warnings = [i for i in result.issues if i.severity == "warning"]
    assert len(warnings) == 1
    assert warnings[0].section == "Detailed Guide"
    assert "below the minimum word count" in warnings[0].message.lower()

def test_lesson_contract_validator_usefulness_indicator():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Practical Application", min_words=150, required=True)
        ]
    )
    # Text has < 50% of 150 words (e.g. 40 words), but has a code block.
    content = "### Practical Application\n" + " word" * 40 + "\n```python\nprint('code')\n```\n"
    result = validate_lesson_contract(content, contract)
    
    # Should be a warning, not a blocker, because code block = useful
    assert result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) == 0
    warnings = [i for i in result.issues if i.severity == "warning"]
    assert len(warnings) == 1
    assert warnings[0].section == "Practical Application"
    
    # Same word count, but NO code block -> should be a blocker.
    content_no_code = "### Practical Application\n" + " word" * 40 + "\n"
    result_no_code = validate_lesson_contract(content_no_code, contract)
    assert not result_no_code.passed
    blockers_no_code = [i for i in result_no_code.issues if i.severity == "blocker"]
    assert len(blockers_no_code) == 1

def test_lesson_contract_validator_hierarchical_parsing():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Practical Application", min_words=20, required=True)
        ]
    )
    content = """### Practical Application

Some intro.

#### Step 1: Definition

This should belong to Practical Application.

#### Step 2: Implementation

This is also part of it.

### Next Section
"""
    result = validate_lesson_contract(content, contract)
    assert result.passed
    # Total words in Practical Application should include child headings
    # Words: "Some intro." (2), "Step 1: Definition" (3), "This should belong..." (6), 
    # "Step 2: Implementation" (3), "This is also part of it." (6) = 20 words
    assert len(result.issues) == 0


def test_lesson_contract_validator_happy_path():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Introduction", aliases=["Intro"], min_words=5, required=True),
            SectionRequirement(title="Exercises", min_words=10, required=True)
        ]
    )
    content = """# Intro
This introduction is more than five words long.
# Exercises
Here is an exercise:
1. Implement a calculator.
2. Run some tests on it.
"""
    result = validate_lesson_contract(content, contract)
    assert result.passed
    assert len(result.issues) == 0

def test_lesson_contract_validator_ignores_fenced_code_comments():
    contract = LessonContract(
        sections=[
            SectionRequirement(title="Introduction", required=True),
            SectionRequirement(title="Core Concepts", required=True),
            SectionRequirement(title="Practical Application", required=True),
            SectionRequirement(title="Summary and Key Takeaways", required=True)
        ]
    )
    
    draft = """# Introduction
This is the intro.

# Core Concepts
These are concepts.

# Practical Application
Here is code.
```python
# 1. The Agent interprets the intent
def parse():
    pass
### Fake heading
```

# Summary and Key Takeaways
We did great things today.
"""
    result = validate_lesson_contract(draft, contract)
    # Buggy behavior breaks parsing inside 'Practical Application' and fails to see 'Summary and Key Takeaways'
    # or flags the fake headings as empty sections.
    # We want NO fake headings in the detected list
    assert "1. The Agent interprets the intent" not in result.detected_headings
    assert "Fake heading" not in result.detected_headings
    
    # We want the real headings
    assert "Summary and Key Takeaways" in result.detected_headings
    
    assert result.passed
    assert len(result.issues) == 0


def test_lesson_contract_validator_heading_rules_level_mismatch():
    contract = LessonContract(
        lesson_contract_name="ottolearn",
        sections=[
            SectionRequirement(title="Hook", required=True, required_level=3),
            SectionRequirement(title="Core Idea", required=True, required_level=4)
        ]
    )
    # Using H2 instead of H3 for Hook, and H3 instead of H4 for Core Idea
    content = """## Hook
This is the hook.

### Core Idea
This is the idea.
"""
    result = validate_lesson_contract(content, contract)
    assert not result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert len(blockers) == 2
    assert any("expected heading level 3" in i.message.lower() for i in blockers)
    assert any("expected heading level 4" in i.message.lower() for i in blockers)

def test_lesson_contract_validator_heading_rules_multiple_main_headings():
    contract = LessonContract(
        lesson_contract_name="ottolearn",
        heading_rules=HeadingRules(
            submodule_heading_level=3,
            main_content_heading=HeadingRuleMainContent(
                canonical="Hook",
                required_level=3,
                must_be_unique_per_submodule=True
            ),
            required_child_section_level=4,
            optional_child_section_level=4,
            walkthrough_step_level=4
        ),
        sections=[
            SectionRequirement(title="Hook", required=True, required_level=3),
            SectionRequirement(title="Core Idea", required=True, required_level=4)
        ]
    )
    # Having multiple H3s is invalid in ottolearn
    content = """### Hook
This is the hook.

#### Core Idea
This is the idea.

### Another H3
This breaks the rule.
"""
    result = validate_lesson_contract(content, contract)
    assert not result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    # At least one blocker regarding multiple H3s
    assert len(blockers) >= 1
    assert any("multiple" in i.message.lower() and "level 3" in i.message.lower() for i in blockers)
