## 2026-06-19T11:02:58Z
You are a Read-only exploration agent. Your working directory is e:\hermes\agentic-course-loop\.agents\explorer_m1\.
Please perform the following exploration:
1. Examine all markdown prompt files under `src/prompts/general/` to identify all python format placeholders (e.g., `{course_name}`, `{duration_weeks}`, etc.).
2. Map these placeholders to the corresponding agent classes and methods in `src/agents/core.py` (e.g. `ContentGenerator.generate`, `Critic.critique_chat`, `Editor.edit_chat`, `Archivist.compress_submodule`, `InternalLibrarian.audit_draft`, `Librarian.audit_structure`, `FactChecker.check_facts`, `StyleSynthesizer.synthesize_rule`, etc.).
3. Identify which variables are missing from the current agent signatures and call sites in `src/agents/core.py`.
4. Check where these methods are invoked in `src/engine/orchestrator.py` and identify how the orchestrator can retrieve these variables from the `course` and `mod` Pydantic schemas (such as `course.course_name`, `course.topic`, `course.duration_weeks`, `mod.module_context`).
5. Write your findings to `analysis.md` and complete your handoff report `handoff.md` in your working directory `e:\hermes\agentic-course-loop\.agents\explorer_m1\`.

Your response MUST follow the standard agent-to-agent messaging format and you should call send_message to report your completion back.
