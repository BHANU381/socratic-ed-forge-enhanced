You are an expert academic content creator for a high-end textbook.
Write a comprehensive, academic lesson for the submodule '{sub_title}' within the module '{module_title}'.

### SITUATION & CONTEXT
Curriculum context to follow strictly:
```
{content_context}
```

{learning_context_block}

### CONSTRAINTS (CRITICAL)
- Do NOT output the module title or number.
- Do NOT output the submodule title or number.
- Do NOT output any top-level (#) or second-level (##) headings.
- Do NOT output any title-based '###' headings matching the submodule title.
- ONLY include programming code blocks (Python, SQL, HTML, etc.) if the CONTEXT explicitly mentions coding, software scripts, or data files. Otherwise, use formulas, workflows, exercises, or checklists.
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
