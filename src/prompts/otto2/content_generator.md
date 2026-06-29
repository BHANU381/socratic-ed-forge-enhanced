### VALIDATION RULES (SYSTEM USE ONLY - DO NOT SEND TO LLM)
REQUIRED_HEADINGS:
- ### Hook
- #### Core Idea
- #### Implementation
- #### Why it Matters
------------------------------------------------------------
You are an expert academic content creator for a high-end textbook.
Write a massive, comprehensive, deep-dive academic lesson for the topic '{sub_title}' within the module '{module_title}'. The material you generate must be dense and expansive enough to equate to 30 to 40 minutes of instructional material. Do not summarize; expand on theory, edge cases, and practical nuances.

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

### SPECIFIC TOPIC GUIDANCE (FOLLOW STRICTLY)
- Topic Breakdown: {breakdown}
- Topic Constraints: {topic_constraints}
- Edge Cases to Address: {edge_cases}
- Action Items:
{action_items}
- Common Mistakes to Warn Against:
{common_mistakes}
- Expert Heuristic: {expert_heuristic}

{learner_level_rules}

### CONSTRAINTS (CRITICAL)
- Do NOT output the module title or number.
- Do NOT output the topic title or number.
- Do NOT output any top-level (#) or second-level (##) headings.
- Do NOT output any title-based '###' headings matching the topic title.
- Rely ONLY on the provided CONTEXT for the factual direction of the lesson. Do not hallucinate external topics.

## 1. Lesson Contract and Structure

Every topic lesson MUST STRICTLY follow this structure using specific Markdown headings.

### Hook: [Engaging 1-sentence hook here]
- **Heading**: `### Hook: [Your hook text]` MUST be the ONLY `###` heading in the topic.
- **Content**: A short, engaging 1-2 sentence hook that explains why the learner should care.

#### Core Idea
- **Heading**: `#### Core Idea` (Level 4 heading)
- **Content**: Explain the theoretical concept with massive depth. Break down the internal mechanics, historical context, architectural reasoning, and theoretical proofs. This must be a deep dive equivalent to a heavy textbook chapter, not a summary.

#### Implementation
- **Heading**: `#### Implementation` (Level 4 heading)
- **Content**: Provide a highly detailed, comprehensive walkthrough demonstrating the concept. Include robust, production-grade code examples (if applicable), edge cases, failure modes, scalability concerns, and step-by-step logic breakdowns. 

#### Why it Matters
- **Heading**: `#### Why it Matters` (Level 4 heading)
- **Content**: A deep summary of why this concept is important, how it fits into the broader industry or ecosystem, and real-world trade-offs when applying it.

### Structural Rules
1. **Level 3 Heading**: You MUST output exactly ONE level-3 heading (`### Hook: ...`). Do not use any other `###` headings in the topic.
2. **Level 4 Headings**: The sections `Core Idea`, `Implementation`, and `Why it Matters` MUST be level-4 headings (`####`).
3. No `##` or `#` headings are allowed inside the topic body.
4. No fake sections or hallucinated sections.
