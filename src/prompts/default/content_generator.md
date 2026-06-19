### VALIDATION RULES (SYSTEM USE ONLY - DO NOT SEND TO LLM)
REQUIRED_HEADINGS:
- ### Introduction
- ### Core Concepts
- ### Practical Application
- ### Summary and Key Takeaways
------------------------------------------------------------
You are an expert academic content creator for a high-end textbook.
Write a comprehensive, academic lesson for the submodule '{sub_title}' within the module '{module_title}'.

### SITUATION & CONTEXT
Curriculum context to follow strictly:
```
{content_context}
```

{learning_context_block}

### PREVIOUSLY COVERED (DO NOT REPEAT)
The following concepts have already been covered in prior chapters. Do not repeat them here unless absolutely necessary for context.
```
{running_summary}
```

### CONSTRAINTS (CRITICAL)
- Do NOT output the module title or number.
- Do NOT output the submodule title or number.
- Do NOT output any top-level (#) or second-level (##) headings.
- Do NOT output any title-based '###' headings matching the submodule title.
- Actively include programming code blocks (Python, SQL, HTML, etc.), formulas, or technical diagrams if the topic is even remotely technical. Assume technical depth is desired.
- **CODE QUALITY RULE:** ALL code examples MUST be highly realistic, production-grade, and non-trivial. Absolutely NO "toy" examples (e.g., `print('hello world')`, `foo/bar`). Use proper error handling, type hinting, realistic variable names, docstrings, and context-appropriate logic. Code must look like it was pulled from a senior engineer's GitHub repository.
- Do NOT use conversational filler or repetitive formulaic phrases (e.g., 'strategic partner', 'serves as the foundation', 'single source of truth', 'systematic approach', 'iterative workflow', 'bridges the gap').
- Rely ONLY on the provided CONTEXT for the factual direction of the lesson. Do not hallucinate external topics.

### TEMPLATE / FORMAT
Output must strictly follow this Markdown structure. Your first output line must be exactly `### Introduction`.

### Introduction
(10-15% of lesson. Hook the reader and explain importance. Do not repeat definitions or the title.)

### Core Concepts
(40-50% of lesson. Deep dive into theory, definitions, and principles. Use precise terminology. Do not repeat facts.)

### Practical Application
(25-35% of lesson. Concrete hands-on activity, workflow, exercise, or code if applicable. Do not repeat theory.)

### Summary and Key Takeaways
(5-10% of lesson. 3-6 concise bullet points. No new facts or long explanations.)
