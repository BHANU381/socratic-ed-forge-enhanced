# Prompt-to-Agent Mapping Analysis

This analysis document maps the prompt template placeholders from `src/prompts/general/` to the corresponding agent classes and methods in `src/agents/core.py`, identifies missing arguments/parameters, outlines how the orchestrator (`src/engine/orchestrator.py`) can retrieve the necessary fields from the `CourseInput`, `Module`, and `Submodule` Pydantic schemas, and highlights theme compatibility blockers.

---

## 1. Placeholder Map per Prompt File

Below is the list of python format placeholders found within each prompt markdown file in `src/prompts/general/`.

| Prompt File | Placeholders Identified | Mapped Agent / Method |
| :--- | :--- | :--- |
| `content_generator.md` | `{course_name}`, `{course_topic}`, `{duration_weeks}`, `{module_title}`, `{module_context}`, `{submodule_title}`, `{content_context}`, `{running_summary}`, `{learned_rules}`, `{source_context}` | `ContentGenerator.generate` |
| `critic.md` | `{course_name}`, `{course_topic}`, `{duration_weeks}`, `{module_title}`, `{module_context}`, `{submodule_title}`, `{content_context}`, `{running_summary}`, `{source_context}`, `{learned_rules}`, `{lesson_draft}` | `Critic.critique` / `Critic.critique_chat` |
| `editor.md` | `{course_name}`, `{course_topic}`, `{duration_weeks}`, `{module_title}`, `{module_context}`, `{submodule_title}`, `{content_context}`, `{running_summary}`, `{learned_rules}`, `{source_context}`, `{lesson_draft}`, `{critic_feedback}` | `Editor.edit` / `Editor.edit_chat` |
| `archivist.md` | `{course_name}`, `{module_title}`, `{submodule_title}`, `{running_summary}`, `{approved_lesson}` | `Archivist.compress_submodule` |
| `eval_curriculum_judge.md` | `{course_json}` | `CurriculumJudgeEval.evaluate` |
| `global_librarian.md` | `{course_name}`, `{curriculum_structure}`, `{complete_course}` | `Librarian.audit_structure` (Note: expects `librarian.md`) |
| `internal_librarian.md` | `{lesson_content}` | `InternalLibrarian.audit_draft` |
| `learning_engine.md` | `{submodule_title}`, `{lesson_draft}`, `{critic_feedback}`, `{approved_lesson}`, `{existing_learned_rules}` | None (No matching agent class in `core.py`) |

---

## 2. Discrepancy & Missing Variables Analysis

Currently, `src/agents/core.py` was developed specifically to support the `default` theme prompt set. When loading templates from the `general` theme, multiple variables are missing from method signatures or are mapped incorrectly, leading to immediate formatting `KeyError` crashes.

### A. `ContentGenerator.generate`
* **Prompt Template**: `src/prompts/general/content_generator.md`
* **Current Method Signature**:
  ```python
  def generate(self, module_title, sub_title, content_context, running_summary="")
  ```
* **Variables Missing / Mismatched**:
  * **Missing completely from signature and `load_prompt` call**: `course_name`, `course_topic`, `duration_weeks`, `module_context`, `source_context`.
  * **Mismatched (causes KeyError)**:
    * The prompt expects `{submodule_title}` but `sub_title` is passed to `load_prompt`.
    * The prompt expects `{learned_rules}` but `learning_context_block` is passed to `load_prompt`.

### B. `Critic.critique` / `critique_chat`
* **Prompt Template**: `src/prompts/general/critic.md`
* **Current Method Signatures**:
  ```python
  def critique(self, draft, content_context)
  def critique_chat(self, chat_session, draft, content_context)
  ```
* **Variables Missing / Mismatched**:
  * **Missing completely from signatures and `load_prompt` call**: `course_name`, `course_topic`, `duration_weeks`, `module_title`, `module_context`, `submodule_title`, `running_summary`, `source_context`, `learned_rules`.
  * **Mismatched (causes KeyError)**:
    * The prompt expects `{lesson_draft}` but `draft` is passed to `load_prompt`.

### C. `Editor.edit` / `edit_chat`
* **Prompt Template**: `src/prompts/general/editor.md`
* **Current Method Signatures**:
  ```python
  def edit(self, draft, feedback, sub_title, content_context)
  def edit_chat(self, chat_session, draft, feedback, sub_title, content_context)
  ```
* **Variables Missing / Mismatched**:
  * **Missing completely from signatures and `load_prompt` call**: `course_name`, `course_topic`, `duration_weeks`, `module_title`, `module_context`, `running_summary`, `source_context`.
  * **Mismatched (causes KeyError)**:
    * The prompt expects `{submodule_title}` but `sub_title` is passed to `load_prompt`.
    * The prompt expects `{learned_rules}` but `learning_context_block` is passed to `load_prompt`.
    * The prompt expects `{lesson_draft}` but `draft` is passed to `load_prompt`.
    * The prompt expects `{critic_feedback}` but `feedback` is passed to `load_prompt`.

### D. `Archivist.compress_submodule`
* **Prompt Template**: `src/prompts/general/archivist.md`
* **Current Method Signature**:
  ```python
  def compress_submodule(self, content)
  ```
* **Variables Missing / Mismatched**:
  * **Missing completely from signature and `load_prompt` call**: `course_name`, `module_title`, `submodule_title`, `running_summary`.
  * **Mismatched (causes KeyError)**:
    * The prompt expects `{approved_lesson}` but `content` is passed to `load_prompt`.

### E. `CurriculumJudgeEval.evaluate`
* **Prompt Template**: `src/prompts/general/eval_curriculum_judge.md`
* **Current Method Signature**:
  ```python
  def evaluate(self, course_name, topic, duration_weeks, outline)
  ```
* **Variables Missing / Mismatched**:
  * **Missing completely**: The method expects individually unpacked values, but the general prompt expects only a single `{course_json}` containing the full curriculum JSON. This leads to a `KeyError: 'course_json'`.

### F. `Librarian.audit_structure`
* **Prompt Template**: `src/prompts/general/global_librarian.md` (Note the filename mismatch: agent calls `librarian.md`)
* **Current Method Signature**:
  ```python
  def audit_structure(self, full_content, content_context=None)
  ```
* **Variables Missing / Mismatched**:
  * **Missing completely**: `course_name`, `curriculum_structure`.
  * **Mismatched (causes KeyError)**:
    * The prompt expects `{complete_course}` but `full_content` is passed to `load_prompt`.
    * **File Mismatch**: The prompt file is named `global_librarian.md` but the agent loads `librarian.md`. This raises a `FileNotFoundError` in `load_prompt`.

### G. `InternalLibrarian.audit_draft`
* **Prompt Template**: `src/prompts/general/internal_librarian.md`
* **Current Method Signature**:
  ```python
  def audit_draft(self, content)
  ```
* **Variables Missing / Mismatched**:
  * **Mismatched (causes KeyError)**:
    * The prompt expects `{lesson_content}` but `content` is passed to `load_prompt`.

### H. `StyleSynthesizer` / `learning_engine.md`
* **Prompt Template**: `src/prompts/general/learning_engine.md` (Note: `StyleSynthesizer` in `core.py` expects `style_synthesizer_rule.md`)
* **Variables Missing / Mismatched**:
  * There is no agent class mapping to `learning_engine.md`.
  * `StyleSynthesizer.synthesize_rule` expects `{critique}` and `{correction}`, but the general theme contains `learning_engine.md` which expects `{submodule_title}`, `{lesson_draft}`, `{critic_feedback}`, `{approved_lesson}`, `{existing_learned_rules}`.
  * Attempting to load the style synthesizer prompts on `general` theme will cause a `FileNotFoundError` for `style_synthesizer_rule.md`.

---

## 3. Pydantic Schema Mapping & Orchestrator Retrievals

To support the richer general prompts, the orchestrator (`src/engine/orchestrator.py`) must extract the missing variables from the `course` (`CourseInput`), `mod` (`Module`), and `sub` (`Submodule`) Pydantic models.

Here is the mapping from the Pydantic schemas to the required prompt variables:

| Required Variable | Pydantic Schema Retrieval Path | Notes / Defaults |
| :--- | :--- | :--- |
| `course_name` | `course.course_name` | String (e.g. "Intro to SQL") |
| `course_topic` / `topic` | `course.topic` | String (e.g. "Relational databases") |
| `duration_weeks` | `course.duration_weeks` | Integer (e.g. 4) |
| `course_json` | `course.model_dump_json(indent=2)` | Formatted course JSON string |
| `module_title` | `mod.title` | String (e.g. "Module 1: Basic Selects") |
| `module_context` | `mod.module_context` | String context guiding the module |
| `submodule_title` | `sub.title` | String (e.g. "Filtering with WHERE") |
| `content_context` | `sub.content_context` | String context guiding the submodule |
| `running_summary` | `running_summary` | Maintained in `orchestrator.py` dynamically |
| `source_context` | `""` | Not in Pydantic schema; defaults to empty string |
| `curriculum_structure`| *Constructed in orchestrator* | Can be built by formatting all module/submodule titles (see below) |

### Curriculum Structure Helper
To construct `{curriculum_structure}` for the Librarian agent, the orchestrator can build it using:
```python
curriculum_structure = ""
for idx, m in enumerate(course.modules):
    curriculum_structure += f"\n- Module {idx+1}: {m.title}\n"
    for s in m.submodules:
        curriculum_structure += f"  - Submodule: {s.title}\n"
curriculum_structure = curriculum_structure.strip()
```

---

## 4. Theme Compatibility Blockers

If the system theme is switched to `general`, the following fatal issues will occur:
1. **KeyErrors**: Standard format keyword mapping mismatches (e.g., passing `content` instead of `lesson_content`, `draft` instead of `lesson_draft`) will crash the execution of `load_prompt`.
2. **FileNotFoundErrors**:
   * `Librarian` attempts to load `librarian.md`, but only `global_librarian.md` exists under `src/prompts/general/`.
   * `StyleSynthesizer` attempts to load `style_synthesizer_rule.md` and `style_synthesizer_duplicate.md`, but neither exists under `src/prompts/general/` (only `learning_engine.md` exists).
   * `FactChecker` attempts to load `fact_checker.md`, which does not exist in `src/prompts/general/`.
   * `CourseQualityJudgeEval` attempts to load `eval_course_quality.md`, which does not exist in `src/prompts/general/`.

### Recommended Resolution Strategies
* **Harmonize Signatures**: Update method signatures in `src/agents/core.py` to accept keyword arguments (`**kwargs`) or use a comprehensive parameter schema that supports both themes.
* **Normalize Parameter Names in `load_prompt`**: Ensure that parameter values passed to `load_prompt` match the placeholders of the loaded template dynamically or alias them inside `core.py`.
* **Handle Missing Files**:
  * Rename `global_librarian.md` to `librarian.md` or update the class loader to dynamically target the correct file.
  * Supply default versions of `fact_checker.md`, `eval_course_quality.md`, and style synthesizer prompts under `src/prompts/general/` or fall back to the `default` folder if they are missing from a custom theme.
