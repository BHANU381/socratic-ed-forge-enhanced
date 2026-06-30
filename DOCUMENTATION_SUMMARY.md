# Project Updates & Calibration Fixes Documentation

This document compiles the comprehensive design updates, calibration rules, validation fixes, and testing profiles implemented on the Socratic Ed-Forge project.

---

## 1. Summary of Work Done

### A. Semantic Evaluator Calibration (`otto2` Theme)
* **Goal**: Prevent false pedagogical structural/length blocks from failing generations under the `otto2` compact lesson format.
* **Modifications**:
  * Rewrote `src/prompts/otto2/semantic_evaluator.md` to calibrate semantic expectations against the active `lesson_contract`.
  * Removed hardcoded rules demanding 30-40 minute lesson depth or 600-word section sizes.
  * Prohibited the evaluator from failing heading structures or required section order if the deterministic validator already passed.
  * Enforced a strict severity policy: semantic blockers are reserved for real pedagogical issues (off-topic content, wrong code, missing/empty sections), while minor deficits are routed to warnings.

### B. Patch Editor Heading Normalization
* **Goal**: Fix splice failures when patching headers containing colons or descriptive text (e.g., `### Hook: Introduction to Agents`).
* **Modifications**:
  * Implemented a utility function `normalize_heading()` in `src/utils/patch_utils.py` that strips hashes, trailing colons, text after colons, and excess whitespace.
  * Updated matching and duplicate checks to evaluate normalized titles.

### C. `target_words` Contract & Schema Decoupling
* **Goal**: Transition word counts from strict blockers to a tiered model (safety floor vs. target depth).
* **Modifications**:
  * Added `target_words: Optional[int] = None` to the `SectionRequirement` model in `src/models/schemas.py`.
  * Updated `src/prompts/otto2/contract.json` and `src/prompts/ottolearn/contract.json` to assign lower hard `min_words` limits (e.g., 180 words) and set `target_words` to 600.
  * Configured `src/validators/lesson_contract_validator.py` to evaluate the tiers:
    * **Below `min_words`**: Blocker ONLY if it contains no useful elements (code, lists, tables).
    * **Between `min_words` and `target_words`**: Warning only.
    * **At/Above `target_words`**: Pass.

### D. Placeholder Validation Exemptions
* **Goal**: Avoid false failures on placeholder-like strings (`[Code Snippet]`, `[Insert Code]`) when used inside instructional material.
* **Modifications**:
  * Updated `classify_placeholder_occurrence` in `src/validators/markdown_validator.py` to classify occurrences as warnings instead of blockers if they appear inside blockquotes, quoted lines, or contexts matching instructional keywords (e.g., `debugging`, `paste`, `comment`).

### E. Context-Aware Export Guard
* **Goal**: Prevent the Export Guard from blocking compilations on valid prose mentions of `"todo"` or anti-pattern code examples.
* **Modifications**:
  * Replaced the simple keyword substring scanner in `src/engine/orchestrator.py` with a line-by-line contextual parser that tracks code blocks (````) and markdown headings.
  * Exempted standalone placeholders under instructional anti-pattern headings (e.g., `### Bad Example`) inside code blocks.
  * Bypassed blocker severity for prose sentences matching instructional keywords (e.g., *"Avoid TODO comments in production PRs"*).
  * Implemented structured diagnostic output reporting the specific rule ID, file name, line number, snippet, and reason when an actual blocker is flagged.

### F. RAG & Search Fallback Specification
* **Goal**: Provide a blueprint for a future hierarchical grounding and Google Search fallback implementation.
* **Modifications**:
  * Created `RAG_AND_FALLBACK_DESIGN.md` in the workspace root mapping out retrieval steps, vector index chunking hierarchy, search scoping query format, and tool sets.

---

## 2. Updated File Map

1. **[schemas.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/models/schemas.py)** — Pydantic schema changes (`target_words`).
2. **[contract.json (otto2)](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/prompts/otto2/contract.json)** — Calibrated `min_words` and `target_words` ranges.
3. **[contract.json (ottolearn)](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/prompts/ottolearn/contract.json)** — Aligned ranges.
4. **[semantic_evaluator.md](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/prompts/otto2/semantic_evaluator.md)** — Calibrated prompts for `otto2`.
5. **[lesson_contract_validator.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/validators/lesson_contract_validator.py)** — Tiered validation logic.
6. **[markdown_validator.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/validators/markdown_validator.py)** — Exempted placeholders in instructional text.
7. **[patch_utils.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/utils/patch_utils.py)** — Normalized heading match logic.
8. **[learning_engine.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/utils/learning_engine.py)** — Noise filtering logic.
9. **[orchestrator.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/src/engine/orchestrator.py)** — Integrated contextual Export Guard checks, uncommented rule recording.
10. **[test_calibration_fixes.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/tests/test_calibration_fixes.py)** — Calibration tests.
11. **[test_export_guard_tdd.py](file:///E:/New%20folder%20(2)/socratic-ed-forge/tests/test_export_guard_tdd.py)** — Export Guard tests.
12. **[RAG_AND_FALLBACK_DESIGN.md](file:///E:/New%20folder%20(2)/socratic-ed-forge/RAG_AND_FALLBACK_DESIGN.md)** — RAG and Google search design document.

---

## 3. Verification Details

All tests have been run locally using Python virtual environments:
* **Total test cases passing**: **155**
* **Command**: `.\venv\Scripts\python.exe -m pytest tests/`
* **Theme verification**: Passes successfully with compilation verification for `default` and `otto2` themes.
