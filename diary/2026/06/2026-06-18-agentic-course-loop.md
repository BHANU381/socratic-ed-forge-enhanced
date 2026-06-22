# 2026-06-18 | Agentic Course Loop Daily Log

## Work Completed Today

### 1. Diagnosed & Fixed Anti-Code Bias Across All Agent Prompts
Identified a systemic problem where the Learning Engine had caused a feedback loop that trained the system to *fear* code blocks and technical theory. The root cause was traced to a hardcoded constraint in `critic.md` and `content_generator.md` (default and beginner_friendly themes) that rejected code blocks unless they were explicitly mentioned in the curriculum context.

**Changes made:**
- Updated `src/prompts/default/critic.md`: Replaced the code-rejection rule with a rule that actively encourages code blocks for STEM and technical topics.
- Updated `src/prompts/default/content_generator.md`: Added `CODE QUALITY RULE` — all code must be production-grade with type hinting, docstrings, and realistic variable names. No `hello world` toy examples.
- Updated `src/prompts/default/editor.md`: Aligned with the generator's new code-positive stance.
- Updated `src/prompts/beginner_friendly/critic.md` and `beginner_friendly/editor.md` with the same correction adapted for an encouraging, beginner tone.
- **Reset `data/learning_loop/style_guide.json`** to clear out the 18+ anti-code rules that had been accumulating.

### 2. Built the "Blueprint" Teaching Style
Created a brand-new prompt theme from scratch at `src/prompts/blueprint/`, scaffolded from the `default` theme and customized to match the instructional framework provided.

**Blueprint theme structure (4 required headings):**
- `### The Blueprint Hook` — Define the goal at high-level intent, not implementation.
- `### The Core Analogy` — Introduce the technical concept via a grounded real-world comparison.
- `### Sandbox Code Implementation` — Hands-on implementation with explicit telemetry and success criteria.
- `### Verification Test` — Dirty Bit validation gate; appends a structured Markdown verification checklist.

**Files created:**
- `src/prompts/blueprint/content_generator.md`
- `src/prompts/blueprint/critic.md` — Rejects drafts with dense prose walls; enforces the analogy requirement.
- `src/prompts/blueprint/editor.md`
- `src/prompts/blueprint/fact_checker.md`, `internal_librarian.md`, `librarian.md` (copied from default)

### 3. Fixed `KeyError: 'critique'` Pipeline Crash
After creating the blueprint editor prompt, the pipeline crashed when the Editor agent was invoked. The Python orchestrator passes the rejection feedback using the variable name `{feedback}`, but the new `blueprint/editor.md` was written with `{critique}`. Fixed the variable name in `blueprint/editor.md`.

## Next Steps
- Create an `AGENT.md` at the project root with full setup and run instructions for new agents.
- Write a test scenario in `data/samples/` to validate the Blueprint theme generates content with the correct 4 headings.
