# Handoff Report

## 1. Observation

- **Observation 1 (Test execution)**: Running `pytest` returned 53 successful test runs.
  ```
  ============================= 53 passed in 31.63s =============================
  ```
- **Observation 2 (General theme outline evaluation template)**: The file `src/prompts/general/eval_curriculum_judge.md` uses the `{course_json}` placeholder at line 17:
  ```markdown
  # COURSE JSON

  {course_json}
  ```
  No other placeholders exist in that file.
- **Observation 3 (Curriculum Evaluation Call)**: In `src/agents/core.py` (lines 616-623), `CurriculumJudgeEval.evaluate` reads:
  ```python
  def evaluate(self, course_name, topic, duration_weeks, outline):
      prompt, _ = load_prompt("eval_curriculum_judge.md", 
                           theme=self.theme,
                           course_name=course_name,
                           topic=topic,
                           duration_weeks=str(duration_weeks),
                           outline=outline)
  ```
- **Observation 4 (Missing files in general theme)**: Listing files in `src/prompts/general/` shows that `eval_course_quality.md`, `fact_checker.md`, `style_synthesizer_duplicate.md`, and `style_synthesizer_rule.md` are absent.
- **Observation 5 (Missing files in beginner_friendly and blueprint themes)**: Listing files in `src/prompts/beginner_friendly/` and `src/prompts/blueprint/` shows that `archivist.md` is absent.
- **Observation 6 (Prompt template loader behavior)**: The `load_prompt` function in `src/utils/prompt_loader.py` (lines 22-23) raises a `FileNotFoundError` if a file is missing in the chosen theme:
  ```python
  if not os.path.exists(filepath):
      raise FileNotFoundError(f"Prompt template '{filename}' not found in theme '{theme}' at {filepath}")
  ```

---

## 2. Logic Chain

- **Step 1**: From Observation 1, all 53 existing tests pass. However, these tests predominantly mock the model calls and do not cover runtime pipelines for non-default themes like `"general"` with evaluations enabled.
- **Step 2**: From Observation 2 and Observation 3, when `theme="general"` is used and curriculum evaluation runs, `load_prompt` is invoked with `theme="general"` and parameters `course_name`, `topic`, `duration_weeks`, and `outline`. Because the template `src/prompts/general/eval_curriculum_judge.md` contains `{course_json}` but does *not* receive a `course_json` key in `kwargs`, `.format()` will throw a `KeyError: 'course_json'`.
- **Step 3**: From Observation 4 and Observation 6, when `theme="general"` is used and fact-checking runs, `FactChecker.check_facts` calls `load_prompt("fact_checker.md", theme="general")`. Since `fact_checker.md` is absent in that folder, this call raises `FileNotFoundError`, causing execution failure.
- **Step 4**: From Observation 5 and Observation 6, when `"beginner_friendly"` or `"blueprint"` is used, calling `Archivist.compress_submodule` results in `load_prompt("archivist.md", theme=...)` raising `FileNotFoundError`. Even though this is caught and logged, context summaries are never appended to the running summary.

---

## 3. Caveats

- **API Mocks**: In-depth API token usage was validated against the implemented tracking logic, but the actual rate limiter behavior under high stress can only be simulated via unit tests due to a lack of live API access.
- **Other themes**: We assumed that custom themes were meant to be fully functional; if they are considered experimental or unused, these errors might not immediately affect the default pipeline but represent clear design flaws.

---

## 4. Conclusion

- **Verdict**: REQUEST_CHANGES.
- **Assessment**: The refactoring correctly integrates schemas, parses metadata, and tracks tokens, but fails when themes other than `"default"` are activated. 
- **Actionable steps**:
  1. Add a fallback mechanism in `load_prompt` to try loading from the `"default"` theme folder if a template file is missing in a custom theme.
  2. Align placeholders in `src/prompts/general/eval_curriculum_judge.md` with what `CurriculumJudgeEval.evaluate` passes (or serialize the `CourseInput` model to `course_json` and pass it).

---

## 5. Verification Method

To verify these findings:
1. Run `pytest` to ensure all 53 tests pass under default conditions.
2. Run the orchestrator with `prompt_theme` set to `"general"` and environment variable `RUN_EVALS=true` to observe the `KeyError` on curriculum evaluation.
3. Run the orchestrator with `prompt_theme` set to `"general"` and `RUN_EVALS=false` to observe `FileNotFoundError` during the fact-checker execution.
