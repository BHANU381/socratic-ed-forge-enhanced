# Changes Report — TDD General Theme Failing Tests

## Overview
As part of the refactoring task, we established a "fail-first" TDD baseline by creating a new test file `tests/test_general_theme_tdd.py` which mocks LLM calls and executes the 10 target methods of the textbook production agents under the `"general"` theme.

## 1. Baseline Test Run Results (Existing Tests)
We ran the existing test suite using `uv run pytest` to establish the current status:
- Total tests: 43
- Passed: 40
- Failed: 3
  - `tests/test_schemas.py::test_telemetry_loop_stats`
  - `tests/test_structural_gates.py::test_validate_draft_invalid_headings`
  - `tests/test_structural_gates.py::test_validate_draft_dynamic_headings`

## 2. Implemented TDD Test File
A new test file `tests/test_general_theme_tdd.py` was created at `e:\hermes\agentic-course-loop\tests\test_general_theme_tdd.py`. It:
- Mocks `google.genai.Client` to prevent actual API calls and handle initialization without keys.
- Instantiates the 6 agents (`ContentGenerator`, `Critic`, `Editor`, `Archivist`, `InternalLibrarian`, `Librarian`) with the `"general"` theme.
- Mocks internal LLM invocation methods: `_run_with_retry` and `_send_message_with_retry`.
- Invokes the 10 target methods:
  1. `generate` (ContentGenerator)
  2. `critique` (Critic)
  3. `critique_chat` (Critic)
  4. `edit` (Editor)
  5. `edit_chat` (Editor)
  6. `compress_submodule` (Archivist)
  7. `audit_draft` (InternalLibrarian)
  8. `repair` (InternalLibrarian)
  9. `audit_structure` (Librarian)
  10. `audit` (Librarian)

## 3. Failing TDD Pytest Output
The tests were executed with `uv run pytest tests/test_general_theme_tdd.py`. All 10 tests failed as expected with the following traceback/errors:

```
=========================== short test summary info ===========================
FAILED tests/test_general_theme_tdd.py::test_content_generator_generate - KeyError: 'course_name'
FAILED tests/test_general_theme_tdd.py::test_critic_critique - KeyError: 'course_name'
FAILED tests/test_general_theme_tdd.py::test_critic_critique_chat - KeyError: 'course_name'
FAILED tests/test_general_theme_tdd.py::test_editor_edit - KeyError: 'course_name'
FAILED tests/test_general_theme_tdd.py::test_editor_edit_chat - KeyError: 'course_name'
FAILED tests/test_general_theme_tdd.py::test_archivist_compress_submodule - KeyError: 'course_name'
FAILED tests/test_general_theme_tdd.py::test_internal_librarian_audit_draft - KeyError: 'lesson_content'
FAILED tests/test_general_theme_tdd.py::test_internal_librarian_repair - AttributeError: 'InternalLibrarian' object has no attribute 'repair'
FAILED tests/test_general_theme_tdd.py::test_librarian_audit_structure - FileNotFoundError: Prompt template 'librarian.md' not found in theme 'general' at E:\hermes\agentic-course-loop\src\prompts\general\librarian.md
FAILED tests/test_general_theme_tdd.py::test_librarian_audit - AttributeError: 'Librarian' object has no attribute 'audit'
============================= 10 failed in 3.88s ==============================
```

These errors validate our TDD "fail first" baseline due to:
- Prompt placeholder variable mismatches (KeyError).
- Naming mismatches (Librarian looking for `librarian.md` but only `global_librarian.md` exists in the `general` directory).
- Missing methods (`repair` on `InternalLibrarian` and `audit` on `Librarian`).
