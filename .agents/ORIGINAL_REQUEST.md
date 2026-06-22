# Original User Request

## Initial Request — 2026-06-19T05:31:14Z

Refactor the Hermes Agentic Course Loop engine (`src/agents/core.py` and `src/engine/orchestrator.py`) to inject expanded course metadata variables into the generalized prompt templates, using test-driven development (TDD).

Working directory: e:/hermes/agentic-course-loop
Integrity mode: demo

## Requirements

### R1. Test-Driven Development (TDD)
Write unit tests using `pytest` in a `tests/` directory that mock the `orchestrator` variables and verify that all agents can successfully call `load_prompt` for the new `general` theme prompts without throwing a `KeyError`. Run these tests to fail first, then implement the code to pass them.

### R2. Agent Signature Refactor (`src/agents/core.py`)
Refactor the agent class methods (e.g., `ContentGenerator.generate`, `Critic.critique_chat`, `Editor.edit_chat`, `Archivist.compress_submodule`, `InternalLibrarian.repair`, `Librarian.audit`) to accept the expanded course metadata (either as individual arguments or a `course_info` dict) and pass them into `load_prompt`. Ensure backwards compatibility for prompts that don't use all variables.

### R3. Orchestrator Data Passing (`src/engine/orchestrator.py`)
Refactor the main generation loop to extract the required variables from the `course` schema (e.g., `course.course_name`, `course.topic`, `course.duration_weeks`, `mod.module_context`) and pass them into the agent calls.

## Acceptance Criteria

### Automated Verification
- [ ] Running `pytest` successfully executes the written unit tests with 0 failures.
- [ ] The `pytest` suite explicitly tests the `ContentGenerator`, `Critic`, `Editor`, and `Archivist` loading the `general` theme prompts.

---
*Next: when approved → delegate via invoke_subagent (see Delegation Protocol)*
