# Quality and Adversarial Review Report

## Review Summary

**Verdict**: REQUEST_CHANGES

The refactoring of the multi-agent course loop (`src/agents/core.py` and `src/engine/orchestrator.py`) is generally well-structured and successful in maintaining compatibility with existing tests. All 53 unit tests pass perfectly. However, the system contains critical vulnerabilities when non-default themes are activated or when evaluations are enabled, leading to inevitable crashes (`KeyError` and `FileNotFoundError`).

---

## Findings

### [Critical] Finding 1: KeyError in `CurriculumJudgeEval.evaluate` for general theme

- **What**: The curriculum judge evaluation prompt `eval_curriculum_judge.md` in the `"general"` theme contains a single placeholder `{course_json}`. However, `CurriculumJudgeEval.evaluate` in `src/agents/core.py` passes `course_name`, `topic`, `duration_weeks`, and `outline` to `load_prompt`, but does *not* pass `course_json`. This mismatch causes a `KeyError: 'course_json'` when `.format()` is called.
- **Where**: `src/agents/core.py` (line 616) and `src/prompts/general/eval_curriculum_judge.md` (line 17).
- **Why**: Running the pipeline with `prompt_theme: "general"` and `RUN_EVALS=true` will crash immediately during the pre-generation evaluation phase.
- **Suggestion**: Ensure that either `evaluate()` provides `course_json` (e.g., by serializing the course metadata) or align the prompt template placeholders in the `"general"` theme with the default theme.

### [Critical] Finding 2: FileNotFoundError for FactChecker in general theme

- **What**: The `"general"` theme folder `src/prompts/general/` does not contain a `fact_checker.md` template.
- **Where**: `src/agents/core.py` (line 556) and `src/prompts/general/`.
- **Why**: Running with `theme="general"` will cause `FactChecker.check_facts` to raise a `FileNotFoundError`, disrupting fact-checking or causing infinite retry loops.
- **Suggestion**: Implement a fallback mechanism in `load_prompt` (`src/utils/prompt_loader.py`) to search the `"default"` theme folder if a template file is missing in the chosen custom theme.

### [Critical] Finding 3: FileNotFoundError for CourseQualityJudgeEval in general theme

- **What**: The `"general"` theme folder `src/prompts/general/` does not contain `eval_course_quality.md`.
- **Where**: `src/agents/core.py` (line 625) and `src/prompts/general/`.
- **Why**: The post-generation quality evaluation phase will fail with a `FileNotFoundError` if the `"general"` theme is used and `RUN_EVALS=true`.
- **Suggestion**: Add the missing template or rely on the fallback mechanism.

### [Major] Finding 4: FileNotFoundError for Archivist in beginner_friendly and blueprint themes

- **What**: The `"beginner_friendly"` and `"blueprint"` theme folders are missing `archivist.md`.
- **Where**: `src/agents/core.py` (line 334) and `src/prompts/beginner_friendly/` / `src/prompts/blueprint/`.
- **Why**: When these themes are used, the `Archivist` fails to load its template. Although caught and logged in the orchestrator, it skips submodule summary generation entirely, rendering context compression non-functional.
- **Suggestion**: Implement prompt template fallback in `load_prompt` or copy `archivist.md` to these directories.

### [Major] Finding 5: FileNotFoundError for StyleSynthesizer in general theme

- **What**: The `"general"` theme folder is missing `style_synthesizer_duplicate.md` and `style_synthesizer_rule.md`.
- **Where**: `src/agents/core.py` (lines 573 and 593).
- **Why**: Invoking the style synthesizer using the general theme raises `FileNotFoundError`.
- **Suggestion**: Implement prompt template fallback in `load_prompt` or copy the files.

---

## Verified Claims

- **Claim 1**: All 53 unit tests pass perfectly.
  - *Verified via*: `run_command` with `pytest` -> **PASS**.
- **Claim 2**: Robust schema parsing and correct extraction of metadata in the loop.
  - *Verified via*: Inspecting Pydantic validations (`CourseInput`) in `src/engine/orchestrator.py` and metadata mapping (`_extract_course_metadata`) in `src/agents/core.py` -> **PASS**.
- **Claim 3**: No KeyErrors or unexpected AttributeErrors when loading prompt templates.
  - *Verified via*: Static analysis of `src/utils/prompt_loader.py` and checking template files -> **FAIL** (as detailed in findings 1–5).

---

## Coverage Gaps

- **Theme-specific runtime testing** — risk level: **medium** — recommendation: Add a test case in `tests/` that fully simulates the orchestrator pipeline for custom themes (like `"general"`) with evaluations enabled to detect template mismatches automatically.

---

## Unverified Items

- **Actual Gemini API call token tracking & rate limiter under high load** — reason not verified: Lack of real API keys in the test environment (mocks were used).

---
---

# Challenge Report (Adversarial Critic)

## Challenge Summary

**Overall risk assessment**: HIGH

While the core multi-agent orchestration logic is robust, it assumes that custom theme prompt templates are fully populated and identical in interface structure to the default templates. Because they are not, activating custom themes will result in immediate execution halts or degraded quality.

## Challenges

### [Critical] Challenge 1: Theme Mismatch Execution Crashes

- **Assumption challenged**: Choosing a prompt theme other than `default` is safe.
- **Attack scenario**: A user requests a course using the `"general"` theme and starts the pipeline.
- **Blast radius**: The orchestrator crashes and leaves the run in a crashed state, either during curriculum path evaluation, fact-checking, or course quality evaluation.
- **Mitigation**: Implement a robust fallback in `load_prompt()` to check the `"default"` theme folder if a template does not exist in the requested theme:
  ```python
  if not os.path.exists(filepath) and theme != "default":
      filepath = os.path.join(os.path.join(PROMPTS_DIR, "default"), filename)
  ```

### [High] Challenge 2: Context Compression Bypass

- **Assumption challenged**: Submodule summaries are always generated and updated in the running summary to manage the context window.
- **Attack scenario**: A user runs the pipeline with the `"beginner_friendly"` theme.
- **Blast radius**: The `Archivist` throws `FileNotFoundError` silently (logged but caught). The `running_summary` is never updated. For long courses, the content generator's context window will eventually overflow or the model will lose track of earlier submodules.
- **Mitigation**: Implement the fallback mechanism mentioned above.

## Stress Test Results

- **Run general theme course generation** -> expected to succeed -> actually fails with `KeyError` (if evals are active) or `FileNotFoundError` -> **FAIL**.
- **Run beginner_friendly theme course generation** -> expected to compress contexts -> actually fails to generate summaries due to missing `archivist.md` -> **FAIL**.
- **Standard execution on default theme** -> compiles course and passes all gates -> **PASS**.

## Unchallenged Areas

- **Concurrency & SSE Streaming** — reason not challenged: Outside the scope of the refactoring files specified.
