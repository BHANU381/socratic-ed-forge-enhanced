## 2026-06-19T05:38:25Z
<USER_REQUEST>
You are a Developer/Worker agent. Your working directory is e:\hermes\agentic-course-loop\.agents\implementer_m3\.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please implement the refactoring as detailed below:
1. In `src/agents/core.py`:
   - Create a module-level helper function (e.g. `_extract_course_metadata(course_info, **kwargs)`) to extract course metadata variables (course_name, course_topic, duration_weeks, module_context, source_context, learned_rules) from either a Pydantic object, a dictionary, or keyword arguments, defaulting any missing variables to empty strings `""` to ensure complete backwards compatibility and prevent KeyErrors.
   - Refactor the agent methods to accept `course_info=None` and `**kwargs`, extract the course metadata using the helper, and pass them to `load_prompt` along with the other required placeholders:
     - `ContentGenerator.generate` (map `submodule_title=sub_title`, `learned_rules=learned_rules` or `learning_context_block`)
     - `Critic.critique` and `Critic.critique_chat` (map `lesson_draft=draft`, and handle `module_title`, `sub_title`, `running_summary`)
     - `Editor.edit` and `Editor.edit_chat` (map `lesson_draft=draft`, `critic_feedback=feedback`, `submodule_title=sub_title`)
     - `Archivist.compress_submodule` (map `approved_lesson=content`, and handle `module_title`, `sub_title`, `running_summary`)
     - Add `InternalLibrarian.repair` accepting `content`, `course_info=None`, and `**kwargs`, passing `content` and `lesson_content=content` to `load_prompt`. Make `InternalLibrarian.audit_draft` call `repair`.
     - Add `Librarian.audit` accepting `full_content`, `curriculum_structure=""`, `course_info=None`, and `**kwargs`. If `self.theme == "general"`, load `"global_librarian.md"`, otherwise `"librarian.md"`. Pass `course_name`, `curriculum_structure`, `complete_course=full_content`, and `full_content=full_content`. Make `Librarian.audit_structure` call `audit`.
2. In `src/engine/orchestrator.py`:
   - Refactor the main loop to extract course variables from the `course` Pydantic model (`course_name`, `topic` as `course_topic`, `duration_weeks`, `module_context` from module model).
   - Dynamically build the `curriculum_structure` string representing the module/submodule hierarchy.
   - Pass these metadata variables or the `course` model when calling agent methods in the loop (generator.generate, critic.critique_chat, editor.edit_chat, internal_librarian.audit_draft, archivist.compress_submodule, librarian.audit_structure).
3. Run pytest:
   - Run `pytest tests/test_general_theme_tdd.py` to verify that all 10 tests now pass.
   - Run the full pytest suite to verify no regressions.
4. Document the exact changes in `changes.md` and write a handoff report in `handoff.md`.
5. Call send_message to report when done.
</USER_REQUEST>
