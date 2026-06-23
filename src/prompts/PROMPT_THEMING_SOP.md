# Prompt Theming SOP

The `Socratic Ed-Forge` engine supports fully swappable prompt themes. A "theme" dictates the persona, structure, formatting rules, and evaluation criteria the agents use to write course content.

## 1. Directory Structure

To create a new theme, create a new directory inside `src/prompts/` (e.g., `src/prompts/my_theme/`).

Inside your theme directory, you **must** provide the following five files:

1. `contract.json` - Defines the structural validation rules.
2. `content_generator.md` - The system prompt for the Content Generator agent.
3. `semantic_evaluator.md` - The system prompt for the Semantic Evaluator agent.
4. `patch_editor.md` - The system prompt for the Patch Editor agent.
5. `archivist.md` - The system prompt for the Archivist agent.

---

## 2. Writing `contract.json`

The `contract.json` file dictates the required sections, headings, and minimum word counts. The Orchestrator STRICTLY enforces this contract against the generated Markdown. If the generator violates this contract, the submodule fails validation.

### Basic Structure

```json
{
  "lesson_contract_name": "my_custom_lesson",
  "sections": [
    {
      "title": "Introduction",
      "aliases": ["Intro", "Getting Started"],
      "required": true,
      "min_words": 50
    },
    {
      "title": "Core Concepts",
      "aliases": ["Theory"],
      "required": true,
      "min_words": 100
    }
  ]
}
```

### Advanced Hierarchical Rules

If your theme requires a strict hierarchical structure (e.g., specific H3s and nested H4s), you can add `heading_rules`.

```json
{
  "lesson_contract_name": "ottolearn",
  "heading_rules": {
    "submodule_heading_level": 3,
    "main_content_heading": {
      "canonical": "Hook",
      "required_level": 3,
      "must_be_unique_per_submodule": true
    },
    "required_child_section_level": 4,
    "optional_child_section_level": 4,
    "walkthrough_step_level": 4
  },
  "sections": [
    {
      "title": "Hook",
      "aliases": ["Hook"],
      "required": true,
      "required_level": 3,
      "min_words": 10
    },
    {
      "title": "Core Idea",
      "aliases": ["The Concept"],
      "required": true,
      "required_level": 4,
      "min_words": 50
    }
  ]
}
```

- **`required_level`**: If set on a section, the validator ensures the heading is exactly that level (e.g., 3 means `###`).
- **`must_be_unique_per_submodule`**: If set to `true`, the validator will throw a blocker if more than one heading at the specified level exists. (Useful for enforcing exactly one `###` heading).

---

## 3. Writing the Prompts

- Ensure your `content_generator.md` instructs the LLM to output EXACTLY the headings defined in `contract.json`. Do not leave ambiguity.
- The `semantic_evaluator.md` should rely on the `{lesson_contract}` interpolation string to evaluate the structure dynamically. Do not hardcode structure rules in the evaluator prompt.
- The `patch_editor.md` should be capable of handling fixes for the structures you defined.

## 4. Usage

To run the pipeline using your new theme, simply specify `prompt_theme="my_theme"` in the `CourseInput`.
