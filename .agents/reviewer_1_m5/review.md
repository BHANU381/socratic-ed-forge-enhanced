# Review Report — src/agents/core.py and src/engine/orchestrator.py

## Review Summary

**Verdict**: REQUEST_CHANGES

The refactored files `src/agents/core.py` and `src/engine/orchestrator.py` implement the course metadata mapping, kwargs popping, and theme compatibility rules well across almost all agent interfaces. However, a critical bug exists in `Librarian.audit_structure()` that will cause a `TypeError` due to duplicate keyword arguments when executing the orchestrator pipeline.

---

## Findings

### [Critical] Finding 1: TypeError on `curriculum_structure` duplicate keyword argument
- **What**: Python `TypeError: audit() got multiple values for keyword argument 'curriculum_structure'` is raised when running the pipeline.
- **Where**: `src/agents/core.py` (lines 533-535)
- **Why**: 
  In `Librarian.audit_structure`, `curriculum_structure` is read using `kwargs.get("curriculum_structure", "")`:
  ```python
  def audit_structure(self, full_content, content_context=None, course_info=None, **kwargs):
      curriculum_structure = kwargs.get("curriculum_structure", "")
      return self.audit(full_content=full_content, curriculum_structure=curriculum_structure, course_info=course_info, **kwargs)
  ```
  Since `curriculum_structure` is in `kwargs` at the call-site in `orchestrator.py` (line 596), it is passed to `self.audit` both explicitly (`curriculum_structure=curriculum_structure`) and inside `**kwargs`.
- **Suggestion**: Use `kwargs.pop()` instead of `kwargs.get()`.
  ```python
  def audit_structure(self, full_content, content_context=None, course_info=None, **kwargs):
      curriculum_structure = kwargs.pop("curriculum_structure", "")
      return self.audit(full_content=full_content, curriculum_structure=curriculum_structure, course_info=course_info, **kwargs)
  ```

### [Minor] Finding 2: Unused local variables in `orchestrator.py`
- **What**: Unused local variables.
- **Where**: `src/engine/orchestrator.py` (lines 278-280)
- **Why**: 
  The variables:
  ```python
  course_name = course.course_name
  course_topic = course.topic
  duration_weeks = course.duration_weeks
  ```
  are defined but never used inside `main()`.
- **Suggestion**: Remove these variables to clean up dead code.

---

## Verified Claims

- **Claim 1**: Course metadata mapping works correctly (course_name, course_topic, duration_weeks, module_context, etc.).
  - *Verification Method*: Inspected `_extract_course_metadata` in `src/agents/core.py` and validated that it maps all expected variables from dicts, Pydantic objects, and kwargs correctly.
  - *Result*: PASS.

- **Claim 2**: Correct handling of keyword arguments and popping of explicit keys to prevent multiple values errors.
  - *Verification Method*: Checked all agent methods to ensure they pop values before unpacking `**kwargs` into `load_prompt`. Found that `Librarian.audit_structure()` fails this check.
  - *Result*: FAIL (due to Finding 1).

- **Claim 3**: Complete backward compatibility for default/blueprint themes.
  - *Verification Method*: Inspected prompt loader format call and verified that Python's `str.format()` ignores unused kwargs, ensuring themes that don't use all variables still load and compile without error.
  - *Result*: PASS.

- **Claim 4**: Run `pytest` to verify all tests pass.
  - *Verification Method*: Executed `pytest` command on the project workspace.
  - *Result*: PASS (53/53 tests passed). Note that the test suite does not cover calling `audit_structure` with a keyword argument `curriculum_structure`, which is why the bug in Finding 1 was not caught by tests.

---

## Coverage Gaps

- **Integration test coverage** — Risk level: Medium. The test suite doesn't execute the full end-to-end `orchestrator.py` or unit test `Librarian.audit_structure` with realistic keyword arguments. We recommend extending tests to cover this.

---

## Unverified Items

- None. All claims and files in scope have been thoroughly verified.
