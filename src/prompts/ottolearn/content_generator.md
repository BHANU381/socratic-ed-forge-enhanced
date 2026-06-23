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

### LEARNER PROFILE & STYLE
- Learner Level: {learner_level}
- Code Example Style: {code_example_style}
- Explanation Depth: {explanation_depth}
- Module Position: {module_position}

{learner_level_rules}

### CONSTRAINTS (CRITICAL)
- Do NOT output the module title or number.
- Do NOT output the submodule title or number.
- Do NOT output any top-level (#) or second-level (##) headings.
- Do NOT output any title-based '###' headings matching the submodule title.
- Rely ONLY on the provided CONTEXT for the factual direction of the lesson. Do not hallucinate external topics.

## 1. Lesson Contract and Structure

Every submodule MUST STRICTLY follow this structure using specific Markdown headings.

### Hook: [Engaging 1-sentence hook here]
- **Heading**: `### Hook: [Your hook text]` MUST be the ONLY `###` heading in the submodule.
- **Content**: A short, engaging 1-2 sentence hook that explains why the learner should care.

#### Core Idea
- **Heading**: `#### Core Idea` (Level 4 heading)
- **Content**: Explain the theoretical concept clearly and concisely.

#### Implementation
- **Heading**: `#### Implementation` (Level 4 heading)
- **Content**: Provide a practical code example, scenario, or walkthrough demonstrating the concept.

#### Why it Matters
- **Heading**: `#### Why it Matters` (Level 4 heading)
- **Content**: A brief summary of why this concept is important and when to use it in the real world.

### Structural Rules
1. **Level 3 Heading**: You MUST output exactly ONE level-3 heading (`### Hook: ...`). Do not use any other `###` headings in the submodule.
2. **Level 4 Headings**: The sections `Core Idea`, `Implementation`, and `Why it Matters` MUST be level-4 headings (`####`).
3. No `##` or `#` headings are allowed inside the submodule body.
4. No fake sections or hallucinated sections.
