# Handoff Report — explorer_m1

## 1. Observation

Direct observations of files and structure:

* **Prompt Files Directory (`src/prompts/general/`)**:
  Listing of `src/prompts/general/` contains exactly 8 files:
  - `archivist.md`
  - `content_generator.md`
  - `critic.md`
  - `editor.md`
  - `eval_curriculum_judge.md`
  - `global_librarian.md`
  - `internal_librarian.md`
  - `learning_engine.md`

  These files contain placeholders in `{}` format. For example:
  - `content_generator.md` line 18: `{course_name}`, line 21: `{course_topic}`, line 24: `{duration_weeks}`, line 27: `{module_title}`, line 30: `{module_context}`, line 33: `{submodule_title}`, line 36: `{content_context}`, line 39: `{running_summary}`, line 42: `{learned_rules}`, line 45: `{source_context}`.
  - `critic.md` line 62: `{lesson_draft}`.
  - `editor.md` line 65: `{critic_feedback}`.
  - `archivist.md` line 37: `{approved_lesson}`.
  - `eval_curriculum_judge.md` line 17: `{course_json}`.
  - `global_librarian.md` line 16: `{course_name}`, line 19: `{curriculum_structure}`, line 25: `{complete_course}`.
  - `internal_librarian.md` line 23: `{lesson_content}`.
  - `learning_engine.md` line 17: `{submodule_title}`, line 23: `{lesson_draft}`, etc.

* **Agent Implementations (`src/agents/core.py`)**:
  - `ContentGenerator.generate` calls `load_prompt("content_generator.md", sub_title=sub_title, module_title=module_title, content_context=content_context, ...)` (lines 257-263).
  - `Archivist.compress_submodule` calls `load_prompt("archivist.md", content=content)` (lines 268-270).
  - `Critic.critique` and `critique_chat` call `load_prompt("critic.md", content_context=content_context, draft=draft)` (lines 275-285).
  - `Editor.edit` and `edit_chat` call `load_prompt("editor.md", sub_title=sub_title, content_context=content_context, feedback=feedback, draft=draft, ...)` (lines 299-324).
  - `Librarian.audit_structure` calls `load_prompt("librarian.md", full_content=full_content)` (lines 328-331).
  - `InternalLibrarian.audit_draft` calls `load_prompt("internal_librarian.md", content=content)` (lines 335-338).
  - `CurriculumJudgeEval.evaluate` calls `load_prompt("eval_curriculum_judge.md", course_name=course_name, topic=topic, duration_weeks=str(duration_weeks), outline=outline)` (lines 402-408).
  - `StyleSynthesizer.synthesize_rule` calls `load_prompt("style_synthesizer_rule.md", critique=critique, correction=correction)` (lines 358-362).
  - `StyleSynthesizer.find_duplicate_rule` calls `load_prompt("style_synthesizer_duplicate.md", rules_formatted=rules_formatted, new_rule=new_rule)` (lines 379-382).
  - `CourseQualityJudgeEval.evaluate` calls `load_prompt("eval_course_quality.md", compiled_course=compiled_course)` (lines 418-421).
  - No class exists in `src/agents/core.py` that references `learning_engine.md`.

* **Prompt Loader Implementation (`src/utils/prompt_loader.py`)**:
  - `load_prompt` returns `template.format(**kwargs)` (line 44). It does not catch or handle missing placeholders, raising `KeyError` if any template placeholders are not matched in `kwargs`.
  - `load_prompt` searches for files in `src/prompts/{theme}/filename` (lines 19-20) and raises `FileNotFoundError` if a file is not found (line 23).

* **Orchestrator Implementation (`src/engine/orchestrator.py`)**:
  - `main` instantiates agents passing `theme=course.prompt_theme` (lines 192-198).
  - Pydantic schema schemas validated via `CourseInput.model_validate(data)` (line 176).
  - Iterates modules and submodules (lines 273, 284) via `for i, mod in enumerate(course.modules)` and `for sub in mod.submodules`.

---

## 2. Logic Chain

1. **Prompt Placeholders**: Comparing the placeholders in `src/prompts/general/` (Observation 1) with the keywords passed to `load_prompt` in `src/agents/core.py` (Observation 2) shows direct mismatches:
   - Mismatched argument names: `sub_title` vs `{submodule_title}`, `draft` vs `{lesson_draft}`, `content` vs `{lesson_content}` / `{approved_lesson}`, `feedback` vs `{critic_feedback}`.
   - Missing required arguments: `course_name`, `course_topic`, `duration_weeks`, `module_context`, `source_context`, `running_summary`, etc.
2. **Crash on Format Injection**: Because `prompt_loader.py` calls `.format(**kwargs)` directly (Observation 3) and raises `KeyError` if kwargs do not cover all template placeholders, switching the prompt theme to `general` will cause the application to crash immediately with formatting `KeyError`s.
3. **Missing Prompt Files**: The `general` theme directory is missing several files expected by default agent implementations (Observation 2 & 3):
   - `Librarian` calls `librarian.md`, but the file in `general` is named `global_librarian.md`.
   - `StyleSynthesizer` calls `style_synthesizer_rule.md` and `style_synthesizer_duplicate.md`, which are missing in `general` (the `general` folder contains `learning_engine.md` instead).
   - `FactChecker` calls `fact_checker.md` and `CourseQualityJudgeEval` calls `eval_course_quality.md`, both of which are missing in the `general` directory.
   - This will cause immediate `FileNotFoundError` crashes when calling these agents with `theme="general"`.
4. **Pydantic Schema Retrieval**: The orchestrator has access to `course` (`CourseInput`), `mod` (`Module`), and `sub` (`Submodule`) Pydantic models (Observation 4). Any missing placeholders (e.g. `course_name`, `topic`, `duration_weeks`, `module_context`) can be retrieved using standard attributes like `course.course_name`, `course.topic`, `course.duration_weeks`, and `mod.module_context`.

---

## 3. Caveats

* **Source Context**: The placeholder `{source_context}` is referenced in several `general` templates. However, there is currently no field in `CourseInput` or `Module` / `Submodule` Pydantic schemas to store source material. The analysis assumes `source_context` should default to an empty string `""` until the schema is extended.
* **StyleSynthesizer Integration**: We assume `learning_engine.md` was intended to replace or extend `style_synthesizer_rule.md` in the `general` theme, but because it expects an entirely different set of arguments (e.g., original draft, critique feedback, approved lesson), it requires rewriting the `StyleSynthesizer` rule-generation logic.

---

## 4. Conclusion

The current codebase in `src/agents/core.py` and `src/engine/orchestrator.py` cannot execute using the `general` prompt theme. Doing so results in:
1. `FileNotFoundError` for `librarian.md` (which is named `global_librarian.md`), `fact_checker.md`, `eval_course_quality.md`, `style_synthesizer_rule.md`, and `style_synthesizer_duplicate.md`.
2. `KeyError` for unmatched placeholders in `content_generator.md`, `critic.md`, `editor.md`, `archivist.md`, and `eval_curriculum_judge.md`.

To make the codebase compatible with the `general` prompts theme, the agent signatures and calls in `core.py` and `orchestrator.py` must be refactored to pass all required variables, utilizing the `course`, `mod`, and `sub` Pydantic schemas to retrieve the missing information.

---

## 5. Verification Method

To verify the findings and check for theme incompatibilities:
1. Try running the orchestrator using the `general` theme by altering the `prompt_theme` in `data/input/course_input.json` to `"general"`.
2. Propose or run a simple python test script that loads the templates via `load_prompt` using `theme="general"`. For example:
   ```python
   from src.utils.prompt_loader import load_prompt
   # This will raise FileNotFoundError:
   load_prompt("librarian.md", theme="general")
   # This will raise KeyError: 'course_name'
   load_prompt("content_generator.md", theme="general", sub_title="Test", module_title="Test", content_context="Test")
   ```
3. Verify that the files listed in the analysis `analysis.md` exist or are missing under `src/prompts/general/` by checking the file paths.
