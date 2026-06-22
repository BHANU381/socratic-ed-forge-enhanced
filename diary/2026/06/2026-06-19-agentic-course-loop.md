# 2026-06-19 | Agentic Course Loop Daily Log

## Work Completed Today

### 1. Discovered & Reviewed the `general` Prompt Theme
Found a fully-featured, 544-line `src/prompts/general/content_generator.md` that was already present in the project. This prompt is significantly more sophisticated than the `default` or `blueprint` themes. Key capabilities:

- **Auto-detects learner level** (beginner → working professional) from the curriculum context.
- **Auto-detects lesson type** (technical, conceptual, vocational, safety, creative, etc.) and selects the appropriate teaching method automatically.
- **Nuanced code rules**: Uses a structured code progression (minimal example → explanation → realistic version → common failure → practice task), avoiding both toy examples and unnecessary production-level complexity for beginners.
- Includes a **silent internal checklist** the LLM runs before returning a lesson.

### 2. Identified Gaps in Blueprint Theme Code Quality
Compared the `blueprint/content_generator.md` against the `default` and `general` versions. Found that the Blueprint theme's `### Sandbox Code Implementation` section is underspecified — it lacks the `CODE QUALITY RULE` that forces production-grade, realistic code rather than pseudocode. This remains an open item for the next session.

### 3. Agent Workspace & Tooling Knowledge Transfer
Discussed and clarified the Antigravity agent workspace system:
- **Rules** vs. **Skills** vs. **Workflows**: Rules are always-on constraints; Skills are on-demand knowledge toolkits (require `SKILL.md` with YAML frontmatter inside their own folder); Workflows are step-by-step procedural guides that become slash commands.
- **YAML frontmatter requirement** for skills: Every `SKILL.md` must have `name:` and `description:` fields at the top.
- **Skills can be nested in `.agents/`**: Confirmed that the `skills/` folder can safely live inside `.agents/` rather than `.agent/`.

### 4. Planned `AGENT.md` Project Entry Point
Designed the full structure for a new `AGENT.md` file at `e:\hermes\agentic-course-loop\AGENT.md` to serve as the canonical onboarding document for any new agent or developer. Planned sections:
- Project overview & architecture
- Directory map
- Environment setup (`GEMINI_API_KEY`, `venv`, `pip install`)
- How to run (full stack via `start.bat`, backend-only, frontend-only, CLI orchestrator)
- How to run the test suite (`python -m pytest tests/`)
- Available prompt styles and what each does
- Key agent constraints (stop flag, style guide, max iteration limit)

> **Pending**: `AGENT.md` creation is pending user approval to start working.

## Open Items for Next Session
- [ ] Create `AGENT.md` at the project root.
- [ ] Add `CODE QUALITY RULE` to `src/prompts/blueprint/content_generator.md`.
- [ ] Create a sample test payload for the Blueprint theme in `data/samples/`.
