# Agent Instructions (Socratic Ed-Forge)

Welcome to the Agentic Course Loop project! As an AI agent working in this repository, please adhere strictly to the following technical rules and guidelines.

## 1. Tech Stack
- **Frontend**: We use **React** for the frontend interface. 
- **Backend**: We use **Python**.
- **Important constraint**: Do **NOT** use, import, or generate code for Streamlit or Chainlit. The stack is strictly React + Python.

## 2. Environment Setup
To set up the environment for autonomous execution:
1. Ensure you are using the local virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Note: Do not commit the `venv/` directory. It is already properly excluded in `.gitignore`.

## 3. Running the Test Suite
We practice Test-Driven Development (TDD). Do not write production code without writing a failing test first.

To run the tests autonomously, use the explicit path to the virtual environment's executable to ensure dependencies are loaded correctly:
```powershell
.\venv\Scripts\python.exe -m pytest tests/
```
Ensure that **all tests pass (0 warnings, 0 errors)** before completing any task.

## 4. General Guidelines
- Do not make changes to `.gitignore` regarding environment folders as they are already set.
- Keep output clean and focus strictly on the Python backend engine and the React frontend architecture.
