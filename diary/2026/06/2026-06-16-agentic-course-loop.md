# Project DevLog: agentic-course-loop
* **📅 Date**: 2026-06-16
* **🏷️ Tags**: `#Project` `#DevLog`

---

> 🎯 **Progress Summary**
> Resolved LLM grounding architecture decisions by validating CAG (Brute Force Flash) as the optimal, most cost-effective path for processing textbooks. Completed backend refactoring for FastAPI, integrating Pydantic schemas, lifespan handlers, and robust testing.

### 🛠️ Execution Details & Changes
* **Core File Modifications**:
  * 📄 `backend/server.py`: Migrated from deprecated `on_event` to standard `lifespan` handlers. Integrated `Pydantic` `CourseInput` for endpoint validation. Migrated `os.path` to `pathlib` for unified path handling.
  * 📄 `tests/test_server.py` & `tests/test_logger.py`: Finalized test suites. Verified 34 passing tests for backend stability.
  * 📄 `implementation_plan.md`: Formally mapped 4 distinct grounding architectures (CAG, Prompt Caching, Vector RAG, Smart Summarization) ordered by cost-effectiveness. 
  * 📄 `wiki/concepts/llm-grounding-strategies.md` & `wiki/concepts/llm-evaluations.md`: Drafted knowledge documents detailing LLM context management strategies and evaluation pipelines based on industry patterns.

* **Technical Implementation**:
  * Adopted Cache Augmented Generation (CAG) utilizing 1M+ token windows (like `gemini-1.5-flash`) as the primary architecture for the project. CAG eliminates vector databases and chunking latency while massively reducing compute cost for stable datasets like textbooks.

### 🚨 Troubleshooting
> 🐛 **Problem Encountered**: Determining the cheapest way to ground the LLM on a large textbook without hallucination. Vector RAG is slow and expensive for single-book scenarios.
> 💡 **Solution**: Selected Brute-Force Flash / Cache Augmented Generation (CAG). It scales cleanly within modern 1M-2M token context windows, enabling instantaneous retrieval at pennies per run.

### ⏭️ Next Steps
- [ ] Implement `src/engine/grounding.py` for injecting textbook text into system prompts (CAG).
- [ ] Build the LLM-as-a-Judge offline evaluation script (`tests/evals/verify_grounding.py`) to mathematically score output faithfulness.
- [ ] Refactor UI component `LogsPanel.jsx` (Fix `Warning: Function components cannot be given refs`).
- [ ] Setup Vitest and React Testing Library for frontend automation.
