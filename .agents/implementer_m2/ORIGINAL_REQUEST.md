## 2026-06-19T05:35:05Z
You are a Developer/Worker agent. Your working directory is e:\hermes\agentic-course-loop\.agents\implementer_m2\.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please do the following:
1. Run the existing tests using `pytest` to establish a baseline.
2. Implement a new TDD test file `tests/test_general_theme_tdd.py` that imports agent classes (ContentGenerator, Critic, Editor, Archivist, InternalLibrarian, Librarian) from `src/agents/core.py` and mocks their LLM interaction methods (`_run_with_retry`, `_send_message_with_retry`, etc.) to return dummy responses, then calls their refactored/target methods (generate, critique, critique_chat, edit, edit_chat, compress_submodule, repair, audit_draft, audit, audit_structure) under the "general" theme.
3. In these tests, pass mock/empty parameters or typical inputs.
4. Run `pytest tests/test_general_theme_tdd.py` to confirm they fail (e.g. with KeyError or FileNotFoundError) because the variables in general theme prompts are not yet supplied or naming is mismatched, and verify that this is indeed a TDD "fail first" step.
5. Provide the command output of the failing tests.

Write your report to `changes.md` and complete your handoff report `handoff.md` in your working directory e:\hermes\agentic-course-loop\.agents\implementer_m2\.
Call send_message to report your progress and completion.
