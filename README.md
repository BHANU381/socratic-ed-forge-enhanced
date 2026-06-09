# Socratic Ed-Forge 🚀

**Socratic Ed-Forge** is a professional-grade, agentic AI engine designed to automate the production of high-quality, textbook-ready educational content. 

Using a sophisticated **Reflective Loop** (Generator $\rightarrow$ Critic $\rightarrow$ Editor), the engine ensures that every module produced meets strict academic standards for technical accuracy, depth, and structural integrity.

## ✨ Key Features

* **Reflective Agentic Loop:** Employs a multi-agent architecture where a **Critic** challenges the **Generator**, and an **Editor** refines the content based on feedback.
* **Librarian Agent:** A specialized structural auditor that ensures Markdown hierarchy and Table of Contents are perfectly aligned.
* **RPM-Aware Pacing:** Intelligent exponential backoff and jitter implementation to handle API rate limits (e.g., Gemini Free Tier) gracefully.
* **Professional Dashboard:** A dual-pane Streamlit interface providing real-time agent logs and a live Markdown preview.
* **Textbook-Grade Output:** Enforced academic tone and structured Markdown hierarchy (`#`, `##`, `###`).

## 🏗️ Architecture

The engine operates on a **Generator-Critic-Editor** pattern:

1.  **Generator:** Drafts the initial technical content based on the input schema.
2.  **Critic:** Audits the draft for technical accuracy and academic depth.
3.  **Editor:** Rewrites the draft to address the Critic's specific feedback.
4.  **Librarian:** Performs a final pass to ensure structural integrity.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd socratic-ed-forge
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add your API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

4. **Run the Dashboard:**
   ```bash
   streamlit run frontend/app.py
   ```

## 📁 Project Structure

```text
socratic-ed-forge/
├── data/               # Input JSONs and generated outputs
├── frontend/           # Streamlit Dashboard
├── src/
│   ├── agents/         # Agent logic (Generator, Critic, etc.)
│   ├── engine/         # Orchestration and loop logic
│   └── utils/          # Helper functions
├── tests/              # TDD test suite
├── .gitignore          # Security and exclusion rules
├── README.md           # Project documentation
└── requirements.txt    # Project dependencies
```

---
*Developed with the Socratic Ed-Forge Engine.*
