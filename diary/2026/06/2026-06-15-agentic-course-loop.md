# Project DevLog: agentic-course-loop
* **📅 Date**: 2026-06-15
* **🏷️ Tags**: `#Project` `#DevLog`

---

> 🎯 **Progress Summary**
> Completed extensive backend refactoring for modern best practices (Pathlib, Pydantic, FastAPI lifespan), achieved 100% test coverage with 34 passing tests including API edge cases, and conducted an architectural brainstorming session regarding LLM grounding and evaluations.

### 🛠️ Execution Details & Changes
* **Core File Modifications**:
  * 📄 `backend/server.py`: Replaced deprecated `on_event("startup")` with `lifespan` context manager. Integrated strict `Pydantic` validation (`CourseInput`) on the `/api/start` endpoint. Converted path logic to `pathlib`.
  * 📄 `src/engine/orchestrator.py` & `src/utils/logger.py`: Upgraded standard `os` file handling to `pathlib` for cross-platform robustness.
  * 📄 `tests/test_server.py`: Added explicit HTTP error testing (e.g., catching `JSONDecodeError` for 400 Bad Request and duplicate process 409 Conflict).
  * 📄 `tests/test_logger.py`: Added edge-case test for global logging when `session_dir` is undefined.

* **Technical Implementation (Architecture & Brainstorming)**:
  * **Frontend Testing Plan (On Hold)**: Drafted an automated testing pipeline using `Vitest` and `React Testing Library` for the React frontend.
  * **LLM Grounding / RAG Design**: Investigated solutions to eliminate parametric memory hallucinations in course generation. Evaluated:
    1. *Prompt Caching* (Gemini 1.5 Pro) - Expensive but high context.
    2. *Local Vector RAG* (ChromaDB) - "Pennies per run", robust, but requires chunking architecture.
    3. *Brute Force Flash* (Gemini 1.5 Flash) - Absolute simplest/cheapest approach, dumping text into prompt.
  * **Evaluations (Evals) Framework**: Established the theoretical design for an offline "LLM-as-a-Judge" pipeline focusing on **Faithfulness**, **Answer Relevance**, and **Context Adherence** to mathematically prove the grounding is working.

### 🚨 Troubleshooting
> 🐛 **Problem Encountered**: `ScrollArea` component in the React frontend throwing a `Warning: Function components cannot be given refs` error.
> 💡 **Solution**: Identified that `src/components/ui/scroll-area.jsx` needs to be wrapped in `React.forwardRef` to allow the LogsPanel to attach its auto-scroll ref. (Fix deferred).

### ⏭️ Next Steps
- [ ] Implement the chosen LLM Grounding architecture (Vector DB vs. Flash brute force).
- [ ] Build the offline Eval script (`LLM-as-a-Judge`) to verify output Faithfulness.
- [ ] Apply the `forwardRef` fix to `scroll-area.jsx` to clear console warnings.
- [ ] Perform a full end-to-end manual generation test via the UI.
