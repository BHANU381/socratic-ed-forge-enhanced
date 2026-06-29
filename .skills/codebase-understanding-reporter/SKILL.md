---
name: codebase-understanding-reporter
description: Guides the agent to inspect a repository, identify its architecture, stack, entry points, data models, and risks, and report these to the user in a structured format.
---

# Codebase Understanding Reporter Skill

## Purpose

Use this skill when the user asks the agent to understand a codebase, inspect a project, explain how the system works, summarize the architecture, or generate a technical report about the repository.

The goal is to help the user quickly understand:

* What the project does
* How the code is structured
* Which files are important
* How the main flows work
* What technologies are used
* What parts are complete, incomplete, risky, or unclear

This skill is for investigation and reporting only. Do not modify code unless the user explicitly asks for code changes.

---

## When To Use This Skill

Use this skill when the user says things like:

* “Understand this codebase and report back.”
* “Tell me how this project works.”
* “Get the idea about the code.”
* “Analyze the repo.”
* “Explain the architecture.”
* “Find the important files.”
* “Tell me what has been implemented.”
* “Give me a report on this project.”
* “Check the flow and summarize it.”

---

## Core Rule

Do not guess.

If something is not clear from the code, say:

> “I could not confirm this from the current files.”

Always separate confirmed findings from assumptions.

---

## Investigation Process

### 1. Start With Repository Overview

First inspect the root directory.

Look for:

* `README.md`
* `package.json`
* `requirements.txt`
* `pyproject.toml`
* `Cargo.toml`
* `pom.xml`
* `go.mod`
* `docker-compose.yml`
* `Dockerfile`
* `.env.example`
* `AGENTS.md`
* `CLAUDE.md`
* `.skills/`
* `docs/`
* `src/`
* `backend/`
* `frontend/`
* `server/`
* `client/`
* `app/`
* `tests/`

Report the high-level project type.

Example:

> “This appears to be a FastAPI backend with a React frontend.”

---

### 2. Identify The Tech Stack

Find and report:

* Programming languages
* Frontend framework
* Backend framework
* Database
* ORM or query layer
* Authentication system
* Testing tools
* Build tools
* Deployment setup
* AI/LLM providers if present
* Background job system if present

Use files like:

* `package.json`
* `requirements.txt`
* `pyproject.toml`
* `vite.config.*`
* `next.config.*`
* `tailwind.config.*`
* `docker-compose.yml`
* `.env.example`

---

### 3. Find Entry Points

Identify how the application starts.

For backend, look for:

* `main.py`
* `server.py`
* `app.py`
* `index.js`
* `server.js`
* `main.ts`
* `Program.cs`

For frontend, look for:

* `main.tsx`
* `main.jsx`
* `App.tsx`
* `App.jsx`
* `pages/`
* `app/`
* `routes/`

For scripts, look for:

* `scripts/`
* `cli.py`
* `commands/`
* `bin/`

Explain the startup flow clearly.

---

### 4. Map The Folder Structure

Create a simple explanation of the important folders.

Example format:

```text
src/
  engine/        Core orchestration logic
  prompts/       Agent prompts and theme-specific instructions
  validators/    Deterministic validation rules
  api/           Backend API routes
  tests/         Unit and integration tests
```

Do not list every file unless necessary. Focus on meaningful folders and core files.

---

### 5. Understand The Main Business Flow

Identify the main user or system flow.

Examples:

* Course generation flow
* Login flow
* Payment flow
* Admin approval flow
* Agent pipeline flow
* Data ingestion flow
* Report generation flow

For each flow, explain:

1. Where it starts
2. Which files are involved
3. What data moves through the system
4. What output is produced
5. Where validation or error handling happens

Use exact file paths when possible.

---

### 6. Inspect Data Models And Contracts

Look for:

* Database schemas
* Pydantic models
* TypeScript interfaces
* Zod schemas
* JSON contracts
* API request/response shapes
* Validation files

Report:

* Main entities
* Important fields
* Relationships
* Validation rules
* Any mismatch between frontend, backend, and database contracts

---

### 7. Inspect Tests

Look for:

* `tests/`
* `__tests__/`
* `*.test.ts`
* `*.spec.ts`
* `pytest`
* `vitest`
* `jest`
* `playwright`
* `cypress`

Report:

* What is tested
* What is not tested
* Whether tests are unit, integration, or end-to-end
* Any important edge cases already covered
* Any risky areas with missing tests

Do not run tests unless the user asks or it is safe and expected.

---

### 8. Inspect AI / Agentic Logic If Present

If the project contains agents, prompts, LLM calls, RAG, validators, or evaluators, inspect:

* Prompt files
* Agent definitions
* Orchestrator files
* Evaluator files
* Contract files
* Retry logic
* Logging / telemetry
* Provider configuration

Report:

* Agent roles
* Pipeline order
* What each agent produces
* How outputs are validated
* Where hallucination or schema drift could happen
* What safeguards exist

---

### 9. Identify Risks And Unknowns

Include a section for:

* Missing documentation
* Incomplete implementation
* Weak validation
* Hardcoded values
* Security concerns
* Missing tests
* Fragile assumptions
* Poor error handling
* Unclear ownership of data
* Areas that need user confirmation

Be honest and specific.

---

## Final Report Format

When finished, report to the user using this structure:

```markdown
# Codebase Understanding Report

## 1. Executive Summary

A short explanation of what this project appears to do.

## 2. Confirmed Tech Stack

- Frontend:
- Backend:
- Database:
- Testing:
- Build/Deployment:
- AI/LLM components:

## 3. Repository Structure

Explain the important folders and files.

## 4. Main Application Flow

Explain the main system flow step by step.

## 5. Important Files

| File | Purpose |
|---|---|
| `path/to/file` | What this file controls |

## 6. Data Models / Contracts

Explain the main data structures, schemas, and validation contracts.

## 7. Agent / AI Pipeline

Only include this section if the project has agentic or AI logic.

Explain:
- Agents involved
- Prompt structure
- Validation flow
- Retry / correction logic
- Output format

## 8. Tests And Quality Checks

Explain what tests exist and what they cover.

## 9. Risks / Issues Found

List concrete risks or weak areas.

## 10. Unknowns

List anything that could not be confirmed from the files.

## 11. Suggested Next Steps

Give practical next steps for the user.
```

---

## Reporting Rules

* Always mention exact file paths when possible.
* Do not invent architecture.
* Do not say something is implemented unless you found evidence in the files.
* Separate confirmed facts from assumptions.
* Keep the report clear enough for a non-expert user.
* Use tables only when they improve readability.
* Do not make code changes unless the user explicitly asks.
* If the repo is too large, inspect the most important files first and state the limits of the analysis.

---

## Default Behavior

When this skill is triggered, the agent should say:

> “I’ll inspect the repository structure, identify the stack, trace the main flows, and then report back with confirmed findings and open questions.”

Then begin the investigation.
