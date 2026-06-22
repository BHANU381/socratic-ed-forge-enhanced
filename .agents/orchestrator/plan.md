# Execution Plan: Hermes Course Loop Refactoring

## Phase 1: Exploration
1. Spawn an Explorer agent to list all variables in the `general` prompts and mapping of variables to agent methods.
2. Explorer details what arguments must be accepted by each of:
   - `ContentGenerator.generate`
   - `Critic.critique_chat` (and `critique`)
   - `Editor.edit_chat` (and `edit`)
   - `Archivist.compress_submodule`
   - `InternalLibrarian.audit_draft` (Wait, does InternalLibrarian use any variables? Let's check R2: "Refactor the agent class methods (e.g., ContentGenerator.generate, Critic.critique_chat, Editor.edit_chat, Archivist.compress_submodule, InternalLibrarian.repair, Librarian.audit)")
     Wait, in R2 it mentions `InternalLibrarian.repair`, but the actual method in core.py is called `audit_draft` (or maybe `repair` is in another branch or should be added/renamed?). Let's check! R2 says: "InternalLibrarian.repair, Librarian.audit". But core.py currently has:
     - `Librarian.audit_structure`
     - `InternalLibrarian.audit_draft`
     Wait! Let's make sure our Explorer locates the exact method names and resolves any discrepancy.
3. Design test strategy to check the behavior of the agents when theme="general".

## Phase 2: TDD Test Implementation
1. Spawn a Worker to write pytest tests under `tests/` (e.g. `tests/test_general_theme_tdd.py`).
2. The tests should:
   - Mock/instantiate `ContentGenerator`, `Critic`, `Editor`, and `Archivist`.
   - Call their respective methods with mocked arguments under the `general` theme.
   - Run pytest and confirm it throws `KeyError` (fail first).

## Phase 3: Agent Signature Refactoring
1. Spawn a Worker to refactor `src/agents/core.py`.
2. Ensure that agent methods accept course metadata variables (either individually or as a dictionary, while keeping backwards compatibility with defaults/kwargs).
3. Ensure that `load_prompt` gets all the required keyword arguments.

## Phase 4: Orchestrator Data Passing Refactor
1. Spawn a Worker to refactor `src/engine/orchestrator.py`.
2. Extract required variables from the Pydantic models/schemas (like `course.course_name`, `course.topic`, `course.duration_weeks`, `mod.module_context`).
3. Pass them when invoking agent methods.
4. Run tests and ensure they pass successfully.

## Phase 5: Verification & Integrity Audit
1. Spawn Reviewers to review implementation and ensure backwards compatibility.
2. Spawn a Challenger to run full test suite and verify edge cases.
3. Spawn Forensic Auditor to verify integrity in demo mode.
