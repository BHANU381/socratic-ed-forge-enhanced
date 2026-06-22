# Project: Hermes Agentic Course Loop Engine Refactor

## Architecture
- **Agents Module (`src/agents/core.py`)**: Defines classes like `ContentGenerator`, `Critic`, `Editor`, `Archivist`, `Librarian`, `InternalLibrarian`. They load prompt templates from `src/prompts/{theme}/` files using `load_prompt`.
- **Engine Module (`src/engine/orchestrator.py`)**: Runs the main generation loop. It loads a course, loops over modules and submodules, invokes agents sequentially, and uses `load_prompt` logic implicitly.
- **Data flow**: Pydantic models (like `CourseInput`, `Module`, `Submodule`) parsed from `course_input.json` in the engine. Variables like `course_name`, `topic`, `duration_weeks`, and module/submodule title/context are extracted and passed down to agents and their `load_prompt` calls.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Exploration and Test Design | Identify prompt variables and plan TDD tests | None | DONE |
| 2 | M2: TDD Test Implementation | Write failing pytest unit tests for KeyError validation | M1 | DONE |
| 3 | M3: Agent Signature Refactoring | Refactor `src/agents/core.py` methods to accept and pass course variables | M2 | DONE |
| 4 | M4: Orchestrator Data Passing | Refactor `src/engine/orchestrator.py` generation loop | M3 | DONE |
| 5 | M5: Verification and Audit | Run tests, Challenger, Reviewer, and Forensic Auditor | M4 | DONE |

## Interface Contracts
### Agent Class Methods ↔ Orchestrator
- Refactored agent methods must accept expanded course metadata (either as individual arguments or a `course_info` dict/object/kwargs).
- Backwards compatibility must be preserved for existing prompts (e.g. `default` or `beginner_friendly` themes) that do not use all the new variables (e.g. by using `**kwargs` or passing default/optional arguments).
- Prompt template files in the `general` theme must format correctly without throwing `KeyError`.

## Code Layout
- `src/agents/core.py` - Agent definitions (ContentGenerator, Critic, Editor, Archivist, InternalLibrarian, Librarian, FactChecker)
- `src/engine/orchestrator.py` - Main course loop orchestration logic
- `src/utils/prompt_loader.py` - Prompts loading utility
- `src/prompts/general/` - Markdown templates for the `general` theme
- `tests/` - Directory for test cases
