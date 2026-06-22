# Handoff Report

## 1. Observation
- **Baseline execution**: Executed `uv run pytest` and observed:
  ```
  FAILED tests/test_schemas.py::test_telemetry_loop_stats - AttributeError: 'TelemetryData' object has no attribute 'stats_passed_first_try'
  FAILED tests/test_structural_gates.py::test_validate_draft_invalid_headings
  FAILED tests/test_structural_gates.py::test_validate_draft_dynamic_headings
  ======================== 3 failed, 40 passed in 34.33s ========================
  ```
- **Prompt files**: Checked `src/prompts/general/` and observed prompt templates such as:
  - `content_generator.md` contains `{course_name}`, `{course_topic}`, `{duration_weeks}`, etc.
  - `internal_librarian.md` contains `{lesson_content}`.
  - There is no file named `librarian.md`, only `global_librarian.md`.
- **Agent implementation**: In `src/agents/core.py`:
  - `ContentGenerator.generate` (lines 245-264) calls `load_prompt("content_generator.md", ...)` passing only `sub_title`, `module_title`, `content_context`, etc., but lacks `course_name` or `course_topic`.
  - `InternalLibrarian.audit_draft` (lines 334-340) calls `load_prompt("internal_librarian.md", ...)` passing `content=content`, not `lesson_content`.
  - `Librarian.audit_structure` (lines 327-333) calls `load_prompt("librarian.md", ...)` which does not exist in `src/prompts/general/`.
  - Methods `repair` (on `InternalLibrarian`) and `audit` (on `Librarian`) are not declared.
- **TDD execution**: Ran `uv run pytest tests/test_general_theme_tdd.py` and observed:
  ```
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

## 2. Logic Chain
1. By calling agent methods configured with `theme="general"` without refactoring their signatures and `load_prompt` logic, they attempt to parse templates from `src/prompts/general/`.
2. These templates use expanded course metadata variables that are not yet passed by `core.py`'s current logic (e.g. `course_name` in `content_generator.md`).
3. Under Python's string format implementation in `src/utils/prompt_loader.py:44`, missing keys raise `KeyError`, which explains the failures in `test_content_generator_generate`, `test_critic_critique`, etc.
4. `InternalLibrarian.audit_draft` passes `content` but the prompt template expects `lesson_content`, raising `KeyError: 'lesson_content'`.
5. `Librarian.audit_structure` looks for `librarian.md` but only `global_librarian.md` exists, explaining `FileNotFoundError`.
6. `InternalLibrarian.repair` and `Librarian.audit` do not exist on the classes yet, resulting in `AttributeError`.
7. Therefore, the failing test suite correctly maps all expected issues and establishes a true "fail first" TDD baseline.

## 3. Caveats
- Checked only the `"general"` theme prompts. Other custom themes (like `beginner_friendly` or `blueprint`) were not analyzed or tested by these new tests since the requirement explicitly specifies tests under the `"general"` theme.

## 4. Conclusion
The general theme TDD test suite (`tests/test_general_theme_tdd.py`) was successfully implemented and run. It fails in all 10 target methods due to missing variables, missing methods, and naming mismatches as expected. This completes the "fail first" step.

## 5. Verification Method
To independently verify:
1. Inspect the test file `tests/test_general_theme_tdd.py`.
2. Run `uv run pytest tests/test_general_theme_tdd.py` in the workspace root directory.
3. Observe all 10 tests failing with the described errors (`KeyError`, `AttributeError`, `FileNotFoundError`).
