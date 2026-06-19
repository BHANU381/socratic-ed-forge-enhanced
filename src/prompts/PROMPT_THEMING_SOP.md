# Prompt Theming Standard Operating Procedure (SOP)

This guide explains how to create and manage dynamic themes for the Agentic Course Loop.

## What is a Theme?
A "theme" is simply a folder inside `src/prompts/` (e.g., `src/prompts/default/` or `src/prompts/beginner_friendly/`). It contains a set of Markdown files that define the persona, tone, rules, and structure for the AI agents (Generator, Editor, Critic, etc.).

## How to Create a New Theme
1. **Create a Folder:** Make a new folder in `src/prompts/` (e.g., `src/prompts/advanced_math/`).
2. **Copy Base Files:** Copy all the `.md` files from `src/prompts/default/` into your new folder.
3. **Customize Tone:** Edit the `.md` files to instruct the AI to use a specific tone (e.g., highly academic, beginner-friendly, sarcastic, etc.).
4. **Define Structure (Dynamic Validation):** 
   You do not need to edit Python code to change the course structure. Instead, open `content_generator.md` in your new theme and define the required headings at the very top of the file:

   ```markdown
   ### VALIDATION RULES (SYSTEM USE ONLY - DO NOT SEND TO LLM)
   REQUIRED_HEADINGS:
   - ### Introduction
   - ### Theory
   - ### Practice
   ------------------------------------------------------------
   ```
   *Note: Ensure the separator line `------------------------------------------------------------` is exactly 60 dashes.*

5. **Update Editor & Critic:** If you changed the headings in `content_generator.md`, make sure you update `editor.md` and `critic.md` in your theme to enforce those exact same headings. The Critic needs to know what structure to demand, and the Editor needs to know how to fix it if it's wrong.

## How it Works Under the Hood
When the Python backend loads `content_generator.md`, the `prompt_loader.py` utility reads the `REQUIRED_HEADINGS` block, extracts the list of headings, and completely strips the validation block before sending the prompt to the LLM. 
The extracted headings are then passed dynamically to the `validate_draft()` and `normalize_draft()` functions in `orchestrator.py`.
