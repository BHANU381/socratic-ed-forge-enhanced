# Socratic Ed-Forge 🚀

**Socratic Ed-Forge** is a professional-grade, agentic AI engine designed to automate the production of high-quality, textbook-ready educational content. 

Using a strict **Deterministic Validation Flow**, the engine replaces unpredictable LLM critique loops with rigid structural rules and targeted semantic evaluation, ensuring every module produced meets strict academic standards without hallucinations.

## ✨ Key Features & New Updates
* **Premium Dark Glassmorphism UI:** A stunning, fully responsive dashboard built with React, Vite, and Shadcn UI. Features frosted glass cards, dynamic background gradients, and native resizable sidebars.
* **RPM & TPM Throttling Controls:** Real-time UI controls to inject specific RPM (Requests Per Minute) and TPM (Tokens Per Minute) limits into the backend engine, ensuring graceful handling of Gemini Free Tier rate limits without crashing.
* **Decoupled Architecture:** 
  * **Frontend:** Lightning-fast React SPA running on Vite.
  * **Backend:** Robust FastAPI orchestrator managing the asynchronous AI agent loop.
* **Deterministic Validation Flow:** Replaces unpredictable multi-agent critique (Critic/Editor/Fact-Checker) with a deterministic Python ruleset that strictly enforces markdown headers, structure, and semantic templates.
* **Knowledge Architect Wiki:** An autonomous, AI-readable Markdown knowledge base (`wiki/`) enforcing a strict Schema structure, frontmatter tracking, and deep linking for codebase documentation.
* **Prompt Modularization:** Hardcoded AI instructions extracted into clean, maintainable Markdown files inside `src/prompts/`.
* **Context-Grounded Generation:** Grounded lesson generation driven by a structured submodule schema containing both `title` and `content_context` (Curriculum Context).
* **Semantic Evaluation & Targeted Patching:** Instead of rewriting entire documents, a **Semantic Evaluator** audits drafts against pedagogical constraints, and a **Patch Editor** surgically fixes broken sections.
* **Topic Isolation & Heading Deduplication:** Ensures submodules do not leak context into each other and programmatically sanitizes top-level headings to prevent duplicate formatting.
* **Archival State Management:** An **Archivist** compresses full lessons into high-fidelity summaries to provide continuous learning context without blowing up the token window.
* **Automated Testing Suite:** Comprehensive suite of Mocked Unit Tests (free, fast, token-less) and Integration Tests inside the `tests/` folder using `pytest` and `MagicMock`.
* **LLM Context Anchors:** Persistent `LLM_CONTEXT.md` documentation acting as the architectural brain for AI agents working on the codebase.
## 🏗️ Architecture

The engine operates on a strict **deterministic validation pipeline**:

1.  **Generator:** Drafts the initial technical content based on the input schema.
2.  **Semantic Evaluator:** Critiques the draft specifically for pedagogical constraints and structural alignment.
3.  **Patch Editor:** Rewrites specific broken sections of the draft based on semantic critique instead of regenerating the entire file.
4.  **Archivist:** Summarizes completed lessons into a concise state to pass as context to the next generation step.
5.  **Validation Gate (Deterministic):** Not an AI agent, but a deterministic Python script that strictly checks if the draft conforms to structural requirements (e.g., enforcing exact headers and markdown structures) before saving to the master file.

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd socratic-ed-forge
   ```

2. **Set up the Backend Environment:**
   Install Python dependencies.
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the Frontend Environment:**
   Install Node.js dependencies for the React app.
   ```bash
   cd frontend-react
   npm install
   cd ..
   ```

4. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

## 🚀 Running the Application

You can start the entire application (both Frontend and Backend) with a single command on Windows:

**Double-click `start.bat`** or run it from the terminal:
```cmd
start.bat
```

This script will automatically:
1. Launch the **FastAPI Backend** on `http://localhost:8000`.
2. Launch the **Vite React Frontend** on `http://localhost:5173`.
3. Open your default web browser to the dashboard.

## 📁 Project Structure

```text
socratic-ed-forge/
├── backend/            # FastAPI orchestration endpoints (server.py)
├── frontend-react/     # React + Vite SPA Dashboard
│   ├── src/
│   │   ├── components/ # Shadcn UI components & Control Panels
│   │   ├── hooks/      # useStream hook for Server-Sent Events (SSE)
│   │   ├── App.jsx     # Main Resizable Panel Layout
│   │   └── index.css   # Dark Glassmorphism tokens
├── src/
│   ├── agents/         # Agent core logic (Generator, Critic, Editor, etc.)
│   ├── engine/         # Task orchestrator and Reflective Loop logic
│   ├── prompts/        # Modularized Markdown instructions for AI agents
│   └── utils/          # Real-time console, rate limiters, and file loggers
├── tests/              # Pytest suite with MagicMock for token-less LLM testing
├── wiki/               # Knowledge Architect Markdown DB
├── LLM_CONTEXT.md      # AI context and architecture rules
├── data/               # Output JSONs and generated markdown (Ignored)
├── .env                # API Keys
├── start.bat           # Easy-start script for Windows
└── requirements.txt    # Python dependencies
```

---
*Developed with the Socratic Ed-Forge Engine.*
