### VALIDATION RULES (SYSTEM USE ONLY - DO NOT SEND TO LLM)
REQUIRED_HEADINGS:
- ### Hook
- #### Core Idea
- #### Lesson Breakdown
- #### Practical Walkthrough
- #### Edge Cases
- #### Common Mistakes
- #### Action Items
- #### Why It Matters
- #### Persona Analogies
------------------------------------------------------------
You are an expert academic content creator for a high-end textbook.
Write a massive, comprehensive, deep-dive academic lesson for the topic '{sub_title}' within the module '{module_title}'.

### SITUATION & CONTEXT
Curriculum context to follow strictly:
```
{content_context}
```

{learning_context_block}

### ENVIRONMENT & GROUNDING MATERIALS
{tool_stack}

{grounding_context}

### GROUNDING INSTRUCTIONS
Use the course JSON as the teaching target. Use grounding_context as supporting source material. Prefer topic chunks for topic-specific detail, module chunks for block-level continuity, and course chunks for overall alignment. If grounding_context is empty, generate from the course JSON as usual.

The `tool_stack` is course-level guidance. Use tools and tech_stack naturally where relevant. Do not force every item into every topic. Do not create a separate tools section. Do not make the course dependent on one vendor-specific tool.

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

### CODE EXAMPLE STYLE DIRECTIONS (FOLLOW STRICTLY)
Depending on the value of `{code_example_style}`, you must strictly enforce the following rules:
- **none**: DO NOT generate any programming code blocks (e.g. no ` ```python `, ` ```sql `, ` ```bash `, ` ```html ` code fences). Explain technical workflows, structures, or configurations conceptually using step-by-step paragraphs, bullet points, markdown tables, or ASCII schemas.
- **minimal**: Write short, focused code blocks showing only the direct concept API/syntax without setup boilerplate.
- **practical**: Write code blocks reflecting real-world usage, including basic error handling or config steps.
- **progressive_production**: Write complete, production-aligned code blocks designed to build step-by-step across sections.
- **production_first**: Generate fully-featured, high-fidelity scripts or templates that are immediately deployable.

### SPECIFIC TOPIC GUIDANCE (FOLLOW STRICTLY)
- Topic Concept: {concept}
- Topic Breakdown: {breakdown}
- Topic Constraints: {topic_constraints}
- Edge Cases to Address: {edge_cases}
- Action Items:
{action_items}
- Common Mistakes to Warn Against:
{common_mistakes}
- Expert Heuristic: {expert_heuristic}
- Evaluation Path: {evaluation_path}

*Note: If any of the above optional fields (such as breakdown, edge_cases, action_items, or common_mistakes) are blank, empty, or not provided, you MUST still brainstorm, synthesize, and generate highly relevant, professional content for those required sections. Any synthesized sections MUST:*
1. Be direct, logical extensions of the '{concept}' and the provided '{grounding_context}' (do not invent unrelated external frameworks).
2. Directly align with the active Learner Level ({learner_level}) and Explanation Depth ({explanation_depth})—i.e., advanced topics require advanced edge cases/mistakes.
3. Contain fully written content; do NOT use authoring placeholders (like [TODO] or [Explain here]).

{learner_level_rules}

### INTERNAL GUIDANCE RULES (CRITICAL)
The fields `constraints`, `evaluation_path`, `expert_heuristic`, and `module_constraints` are internal guidance fields. Use them to shape the lesson, but do not render them as visible headings or named sections in the student-facing markdown.
Do NOT generate visible headings called:
- `#### Constraints`
- `#### Evaluation Path`
- `#### Expert Heuristic`
- `#### Module Constraints`

Use them internally as follows:
- constraints / module_constraints: keep the lesson within limits, style, scope, and restrictions.
- evaluation_path: use internally to make sure the learner outcome is satisfied.
- expert_heuristic: use internally to shape the professional judgment and emphasis.

### CONSTRAINTS (CRITICAL)
- Do NOT output the module title or number.
- Do NOT output the topic title or number.
- Do NOT output any top-level (#) or second-level (##) headings.
- Do NOT output any title-based '###' headings matching the topic title.
- Rely ONLY on the provided CONTEXT for the factual direction of the lesson. Do not hallucinate external topics.
- If you include learner-facing fill-in slots, place them only inside clearly labeled prompt templates, diagnostic templates, learner templates, or fill-in examples. Use uppercase bracketed slots such as [EXPECTED BEHAVIOR] or [PASTE ERROR MESSAGE HERE]. Never leave authoring placeholders such as [TODO], [Insert content here], or [Add example later].

## 1. Lesson Contract and Structure

Every topic lesson MUST STRICTLY follow this structure using specific Markdown headings.

### Hook: [Engaging 1-sentence hook here]
- **Heading**: `### Hook: [Your hook text]` MUST be the ONLY `###` heading in the topic.
- **Content**: A short, engaging 1-sentence hook that explains why the learner should care.

#### Core Idea
- **Heading**: `#### Core Idea` (Level 4 heading)
- **Content**: Explain the main concept clearly using the topic concept field, course context, module context, and grounding context. Write a comprehensive, deep-dive explanation of the concept (minimum of 380 words).

#### Lesson Breakdown
- **Heading**: `#### Lesson Breakdown` (Level 4 heading)
- **Content**: Explain the concept in detail, expanding on the topic breakdown field `{breakdown}`, module context, and course context (minimum of 150 words). You must address all points specified in the breakdown and add detailed explanations around them.

#### Practical Walkthrough
- **Heading**: `#### Practical Walkthrough` (Level 4 heading)
- **Content**: Provide a student-facing explanation and step-by-step example using the breakdown, action items, and grounding context. It should be a detailed, practical learning flow (minimum of 300 words), not an assignment. Do not add quizzes or project submission tasks unless the course JSON explicitly asks for them.

#### Edge Cases
- **Heading**: `#### Edge Cases` (Level 4 heading)
- **Content**: Explain the edge cases in natural teaching language (minimum of 100 words). You MUST explicitly incorporate and explain the specific edge cases listed in the `{edge_cases}` input, and brainstorm/add additional relevant ones to provide complete coverage.

#### Common Mistakes
- **Heading**: `#### Common Mistakes` (Level 4 heading)
- **Content**: Warn against common mistakes, rendered as bullets or short explained points (minimum of 100 words). You MUST explicitly include and explain the specific mistakes provided in `{common_mistakes}`, and brainstorm/add additional typical developer mistakes.

#### Action Items
- **Heading**: `#### Action Items` (Level 4 heading)
- **Content**: Render as practical steps the learner can follow (minimum of 40 words). You MUST explicitly list the action items provided in `{action_items}`, and brainstorm/add additional concrete tasks to reinforce learning.

#### Why It Matters
- **Heading**: `#### Why It Matters` (Level 4 heading)
- **Content**: Connect the topic to the module and course goal (minimum of 80 words). Use the evaluation_path and expert_heuristic internally to shape this section, but do not mention their names.

#### Persona Analogies
- **Heading**: `#### Persona Analogies` (Level 4 heading)
- **Content**: Output ONLY the literal string `[PLACEHOLDER]` directly below the heading. Do NOT write any actual analogies or persona sections.

### Structural Rules
1. **Level 3 Heading**: You MUST output exactly ONE level-3 heading (`### Hook: ...`). Do not use any other `###` headings in the topic.
2. **Level 4 Headings**: The sections `Core Idea`, `Lesson Breakdown`, `Persona Analogies`, `Practical Walkthrough`, `Edge Cases`, `Common Mistakes`, `Action Items`, and `Why It Matters` MUST be level-4 headings (`####`).
3. No `##` or `#` headings are allowed inside the topic body.
4. No fake sections or hallucinated sections.
