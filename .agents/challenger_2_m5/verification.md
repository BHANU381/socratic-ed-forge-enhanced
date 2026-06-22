# Empirical Verification Results

This report documents the empirical verification of the refactored course generation engine under different `prompt_theme` settings and the execution of the unit test suite.

## 1. Unit Test Suite Results

Running `pytest` on the entire test suite confirms that the unit tests are fully correct and passing:
- **Command:** `python -m pytest`
- **Result:** `53 passed`
- **Duration:** 30.02s
- **Details:** All unit tests for agents, schemas, structural gates, logger, server, and curriculum grounding passed without failures.

---

## 2. Main Loop Verification with `prompt_theme: "default"`

The pipeline was executed using a single-module, single-submodule configuration with `prompt_theme` set to `"default"` and using a mocked Gemini client.

### Observations:
1. **Pre-generation Curriculum Path Judge:** Succeeded without crashes (when evals enabled).
2. **Main Loops (Generator, Critic, Fact-Checker, Internal Librarian, Archivist):** Executed without any crashes, KeyErrors, or FileNotFoundErrors.
3. **Librarian Pass Crash (Non-Fatal):** The Librarian's structural audit failed with the following traceback/error:
   `Error: Librarian/Eval error: src.agents.core.Librarian.audit() got multiple values for keyword argument 'curriculum_structure'`
   - **Reason:** In `Librarian.audit_structure`, `curriculum_structure` is passed as a keyword argument and also unpacked via `**kwargs` into `self.audit`, causing a duplicate keyword argument TypeError.
   - **Severity:** Non-fatal for the orchestrator (caught in try/except), but blocks the execution of the Librarian structural audit.

---

## 3. Main Loop Verification with `prompt_theme: "general"`

The pipeline was executed under the same configuration with `prompt_theme` set to `"general"`.

### Observations:
1. **Pre-generation Curriculum Path Judge KeyError:**
   `Error: Curriculum Eval encountered an error, continuing pipeline... 'course_json'`
   - **Reason:** The prompt template `src/prompts/general/eval_curriculum_judge.md` requires `{course_json}`, but `CurriculumJudgeEval.evaluate()` does not pass it (it passes `course_name`, `topic`, `duration_weeks`, and `outline`).
2. **Fact-Checker Auditing FileNotFoundError:**
   `Error: Agent error: Prompt template 'fact_checker.md' not found in theme 'general' at E:\hermes\agentic-course-loop\src\prompts\general\fact_checker.md`
   - **Reason:** The `general` theme directory is missing the `fact_checker.md` template. This causes a `FileNotFoundError` during the fact-checking loop, which subsequently bypasses the fact-checking gate after 3 retry loops.
3. **Librarian Pass Crash (Non-Fatal):**
   `TypeError: src.agents.core.Librarian.audit() got multiple values for keyword argument 'curriculum_structure'` (same issue as `"default"` theme).
4. **Post-generation Course Quality Judge FileNotFoundError (Predicted/Bypassed):**
   Because the Librarian pass raised an exception, the post-generation quality evaluation was skipped. However, because `eval_course_quality.md` does not exist in `src/prompts/general/`, it would have raised a `FileNotFoundError` if it had run.
5. **Missing StyleSynthesizer Templates:**
   The `general` theme directory is missing `style_synthesizer_rule.md` and `style_synthesizer_duplicate.md`. If the `StyleSynthesizer` agent runs, it will raise `FileNotFoundError`.
