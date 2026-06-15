# Socratic Ed-Forge: LLM Context & Onboarding

**Target Audience:** Any Large Language Model (LLM) or AI Agent joining this workspace.
**Purpose:** Provide full context on what this project is, how the architecture works, what the current goals are, and the strict rules to follow.

---

## 1. Project Overview
This project, internally referred to as the **Agentic Course Loop** (or "Socratic Ed-Forge"), is an autonomous, multi-agent pipeline designed to generate high-quality, long-form educational courses (markdown books) based on a JSON configuration (`course_input.json`).

It is not a simple single-prompt generator. It utilizes a **Reflective Loop** with distinct personas (agents) that draft, critique, fact-check, and edit content iteratively until it passes strict deterministic and qualitative gates.

## 2. System Architecture

The system is split into three main components:

### A. The Engine (`src/`)
The core pipeline (`src/engine/orchestrator.py`) sequentially builds the course module by module, submodule by submodule.
- **Agents (`src/agents/core.py`):**
  - **Generator:** Drafts the initial markdown content.
  - **Deterministic Gate:** A hardcoded Python function (`validate_draft`) that strictly enforces formatting (e.g., specific `###` headings, no major `#` headers in submodules).
  - **Critic:** Reviews the draft for tone, flow, and educational depth.
  - **Fact-Checker:** Strictly audits the text for factual inaccuracies, hallucinations, or contradictions against the provided context.
  - **Editor:** Acts on feedback from the Validator, Critic, and Fact-Checker to repair the draft.
  - **Librarian:** Performs a final structural audit of the entire compiled markdown book.
- **Learning Engine (`src/utils/learning_engine.py`):** 
  Instead of injecting raw past errors into prompts (which burns tokens), a `StyleSynthesizer` Agent analyzes corrections and extracts single-sentence rules into a centralized `style_guide.json`. This makes the agents get smarter over time without bloating the context window.

### B. The Backend (`backend/server.py`)
A **FastAPI** server that acts as the bridge between the Engine and the Frontend.
- It launches the orchestrator as a separate, detached process using `sys.executable` and `subprocess.CREATE_NEW_PROCESS_GROUP`.
- It streams real-time updates (logs, telemetry JSON, and live markdown previews) to the frontend via Server-Sent Events (SSE) at `/api/stream`.
- **CRITICAL NOTE ON PROCESS MANAGEMENT:** Windows process management is tricky. The backend uses a robust 3-layer kill mechanism (primarily `taskkill /F /T /PID <pid>`) to ensure the orchestrator and all its child threads are completely terminated when the user hits "Stop". `os.kill` is unreliable for this and leaves zombie processes.

### C. The Frontend (React/Vite Dashboard)
A sleek, dark-mode React dashboard that visualizes the multi-agent process. It connects to the SSE stream to display the active agent, progress percentages, token usage, real-time logs, and a rendered markdown preview. **The frontend relies heavily on the sequential writing of `telemetry.json` and the `.md` master file to display progress.**

---

## 3. The Wiki (Knowledge Architect Pattern)
The documentation is stored in the `wiki/` directory and follows a strict **Knowledge Architect** paradigm.
- **Rule of Law:** You must strictly follow the rules defined in `wiki/SCHEMA.md`.
- **Structure:** 
  - `raw/`: Immutable source material (papers, transcripts). Never modify these.
  - `entities/`: People, tools, agents (e.g., `fact-checker.md`).
  - `concepts/`: Abstract ideas or architectures (e.g., `generator-validator-pattern.md`).
  - `index.md`: The map/catalog of all pages.
  - `log.md`: An append-only chronological action log.
- **Wikilinks:** Use `[[Page Name]]` syntax to heavily interlink documents.

---

## 4. Current Status & Immediate Goals
- **Backend Refactoring (ON HOLD):** We have a pending plan to upgrade the backend using advanced Python/FastAPI patterns. This includes using **Pydantic** models to validate `course_input.json`, adding strict type hinting, modernizing with `pathlib`, and implementing non-blocking I/O (`asyncio.to_thread`) for file operations. *Do not implement this until the user explicitly requests it.*
- **Current Goal:** Maintain the stability of the multi-agent loop, ensure the Fact-Checker and Critic operate smoothly, and expand the wiki as needed. 

---

## 5. Strict Rules for LLMs

1. **NO SHELL COMMANDS FOR FILE MANAGEMENT:** Do not use `bash` or `cmd` to move, rename, or delete files (e.g., no `mv`, `rm`, `cat`, `grep`). Always use your native file-editing and reading tools.
2. **DO NOT BREAK THE SSE STREAM:** Any modifications to `orchestrator.py` or `server.py` must respect the fact that the React frontend expects `telemetry.json` and the markdown files to be updated sequentially. Do not introduce full `asyncio` concurrency for the generation loops without a major architectural overhaul, as it will break the live preview.
3. **LOGGING:** All telemetry and logs must be cleanly written to `data/telemetry.json` and `data/logs.txt` so the frontend can parse them.
4. **WIKI COMPLIANCE:** Every time you create a new concept or architectural decision, log it in `wiki/log.md` and link it appropriately in `wiki/index.md`.
