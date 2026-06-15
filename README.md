# Socratic Ed-Forge 🚀

**Socratic Ed-Forge** is a professional-grade, agentic AI engine designed to automate the production of high-quality, textbook-ready educational content. 

Using a sophisticated **Reflective Loop** (Generator $\rightarrow$ Critic $\rightarrow$ Editor), the engine ensures that every module produced meets strict academic standards for technical accuracy, depth, and structural integrity.

## ✨ Key Features & New Updates
* **Premium Dark Glassmorphism UI:** A stunning, fully responsive dashboard built with React, Vite, and Shadcn UI. Features frosted glass cards, dynamic background gradients, and native resizable sidebars.
* **RPM & TPM Throttling Controls:** Real-time UI controls to inject specific RPM (Requests Per Minute) and TPM (Tokens Per Minute) limits into the backend engine, ensuring graceful handling of Gemini Free Tier rate limits without crashing.
* **Decoupled Architecture:** 
  * **Frontend:** Lightning-fast React SPA running on Vite.
  * **Backend:** Robust FastAPI orchestrator managing the asynchronous AI agent loop.
* **Synthesized Style-Guide Engine (Self-Learning):** Replaces raw experience replay. Condenses errors into single-sentence rules (`style_guide.json`) to slash prompt context bloat by 97.5% and prevent rate limits.
* **Knowledge Architect Wiki:** An autonomous, AI-readable Markdown knowledge base (`wiki/`) enforcing a strict Schema structure, frontmatter tracking, and deep linking for codebase documentation.
* **Prompt Modularization:** Hardcoded AI instructions extracted into clean, maintainable Markdown files inside `src/prompts/`.
* **Context-Grounded Generation:** Grounded lesson generation driven by a structured submodule schema containing both `title` and `content_context` (Curriculum Context).
* **Reflective Agentic Loop:** Employs a multi-agent architecture where a **Critic** challenges the **Generator**, a **Fact-Checker** audits technical accuracy, and an **Editor** refines the content.
* **Topic Isolation & Heading Deduplication:** Ensures submodules do not leak context into each other and programmatically sanitizes top-level headings to prevent duplicate formatting.
* **Dual-Librarian Architecture:** An **Internal Librarian** operates within the loop to enforce strict markdown compliance per submodule, and a **Global Librarian** performs a full-book parse at the end of the course to verify global structure and Table of Contents.
* **Automated Testing Suite:** Comprehensive suite of Mocked Unit Tests (free, fast, token-less) and Integration Tests inside the `tests/` folder using `pytest` and `MagicMock`.
* **LLM Context Anchors:** Persistent `LLM_CONTEXT.md` documentation acting as the architectural brain for AI agents working on the codebase.
## 🏗️ Architecture

The engine operates on a sophisticated **multi-stage validation pipeline**:

1.  **Generator:** Drafts the initial technical content based on the input schema.
2.  **Deterministic Validation Gate:** Checks structural layout (headers, duplicates) programmatically.
3.  **Critic:** Audits the draft for technical accuracy, academic tone, and depth of explanation.
4.  **Fact-Checker:** If the Critic approves, this agent performs a deep audit to identify technical hallucinations or incorrect code.
5.  **Internal Librarian:** Audits the structural formatting and markdown tags of the draft.
6.  **Editor:** If the Critic, Fact-Checker, or Internal Librarian identifies issues, the Editor rewrites the draft based on specific feedback.
7.  **Global Librarian:** Performs a single final pass on the fully compiled book to ensure macroscopic structural integrity and Table of Contents alignment.

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
