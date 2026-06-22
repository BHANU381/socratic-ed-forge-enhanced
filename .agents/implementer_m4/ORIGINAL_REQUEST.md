## 2026-06-19T05:56:10Z
Please implement the following fixes:
1. In `src/utils/prompt_loader.py`'s `load_prompt`:
   - If `os.path.exists(filepath)` is False, check if the file exists under the "default" theme folder (i.e. `os.path.join(PROMPTS_DIR, "default", filename)`). If it exists, use that path. Otherwise, raise `FileNotFoundError`.
2. In `src/agents/core.py`:
   - Refactor `Librarian.audit_structure` to pop `curriculum_structure`, `full_content`, `content_context`, and `course_info` from `kwargs` before calling `self.audit`.
   - Pop any conflicting wrapper arguments in other wrapper methods (like `InternalLibrarian.audit_draft`) before calling the target method.
   - Refactor `CurriculumJudgeEval.evaluate` signature to accept `course_info=None` and `**kwargs`, call `_extract_course_metadata`, pop explicit keys (course_name, topic, duration_weeks, outline, course_json), and pass `course_json=outline` (or `course_json` from kwargs) to `load_prompt`.
3. In `tests/test_general_theme_tdd.py`:
   - Add a test for `CurriculumJudgeEval.evaluate` under `"general"` theme to verify it formats correctly.
4. Run `pytest` to verify that all tests (including the new one) pass successfully.
5. Write your changes in `changes.md` and your handoff report in `handoff.md`.
6. Call send_message to report completion.
