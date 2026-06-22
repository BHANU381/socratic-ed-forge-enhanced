# Code Changes

Implemented the requested fixes:

1. **`src/utils/prompt_loader.py`**:
   - Refactored `load_prompt` to check if a file exists under the `"default"` theme folder (i.e. `os.path.join(PROMPTS_DIR, "default", filename)`) if it is not found under the specified theme path (`os.path.exists(filepath)` is False). If found, it uses the default file path; otherwise, it raises `FileNotFoundError`.

2. **`src/agents/core.py`**:
   - Refactored `Librarian.audit_structure` to pop `curriculum_structure`, `full_content`, `content_context`, and `course_info` from `kwargs` before calling `self.audit`.
   - Refactored `InternalLibrarian.audit_draft` to pop `content` and `course_info` from `kwargs` before calling `self.repair`.
   - Refactored `CurriculumJudgeEval.evaluate` signature to `evaluate(self, course_info=None, **kwargs)`. It calls `_extract_course_metadata` to retrieve metadata, pops explicit keys (`course_name`, `topic`, `duration_weeks`, `outline`, `course_json`) from `merged_kwargs`, and passes `course_json` (resolved from `kwargs.get("course_json", outline)`) to `load_prompt`.

3. **`tests/test_general_theme_tdd.py`**:
   - Added `test_curriculum_judge_eval_evaluate` to verify that `CurriculumJudgeEval.evaluate` under `"general"` theme formats correctly and uses the correct parameters.
