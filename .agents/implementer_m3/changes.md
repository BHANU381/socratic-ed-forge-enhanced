# Refactoring Changes for Course Loop Metadata

## 1. `src/agents/core.py`
- Implemented a module-level helper `_extract_course_metadata(course_info=None, **kwargs) -> dict`. It safely extracts course metadata variables:
  - `course_name`
  - `course_topic`
  - `duration_weeks`
  - `module_context`
  - `source_context`
  - `learned_rules`
  It checks `kwargs` first, then inspects `course_info` (which could be a dictionary, Pydantic model, or generic object). If any variable is missing, it defaults to `""` to ensure complete backwards compatibility and prevent KeyErrors.
- Refactored agent methods to accept `course_info=None` and `**kwargs`, call `_extract_course_metadata`, merge the metadata with `kwargs`, and pop the explicit arguments to prevent `TypeError: got multiple values for keyword argument` from Python. The modified methods are:
  - `ContentGenerator.generate` (maps `submodule_title=sub_title`, `learned_rules=learned_rules` or `learning_context_block`).
  - `Critic.critique` and `Critic.critique_chat` (maps `lesson_draft=draft`, handling `module_title`, `sub_title`, `running_summary`).
  - `Editor.edit` and `Editor.edit_chat` (maps `lesson_draft=draft`, `critic_feedback=feedback`, `submodule_title=sub_title`).
  - `Archivist.compress_submodule` (maps `approved_lesson=content`, handling `module_title`, `sub_title`, `running_summary`).
  - Added `InternalLibrarian.repair` accepting `content`, `course_info=None`, and `**kwargs`, passing `content` and `lesson_content=content` to `load_prompt`.
  - Refactored `InternalLibrarian.audit_draft` to call `repair`.
  - Added `Librarian.audit` accepting `full_content`, `curriculum_structure=""`, `course_info=None`, and `**kwargs`. If `self.theme == "general"`, it loads `"global_librarian.md"`, otherwise `"librarian.md"`. Passes `curriculum_structure`, `complete_course=full_content`, and `full_content=full_content`, along with `course_name` from merged metadata.
  - Refactored `Librarian.audit_structure` to call `audit`.

## 2. `src/engine/orchestrator.py`
- Refactored the main loop to extract course variables (`course_name`, `course_topic`, `duration_weeks`, and `module_context` from the module model).
- Dynamically built the `curriculum_structure` string representing the module/submodule hierarchy.
- Passed these metadata variables or the `course` model when calling agent methods in the loop:
  - `generator.generate`
  - `critic.critique_chat`
  - `editor.edit_chat` (at all validation, fact-check, and critic edit stages)
  - `internal_librarian.audit_draft`
  - `archivist.compress_submodule`
  - `librarian.audit_structure`
- Fixed `validate_draft` to check the prefix before `required_headings[0]`. Only strip conversational prefix if the prefix contains no heading lines (starting with `#`), ensuring out-of-order or illegal high-level headings are correctly preserved for validation.

## 3. `tests/test_schemas.py`
- Corrected the outdated fields in `test_telemetry_loop_stats` (`stats_passed_first_try`, `stats_passed_after_edits`, `stats_failed_max_iterations`) to use the actual Pydantic schema attributes (`passed_1st_iteration`, `passed_2nd_iteration`, `failed_max_iterations`).
