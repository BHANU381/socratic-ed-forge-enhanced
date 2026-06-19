### VALIDATION RULES (SYSTEM USE ONLY - DO NOT SEND TO LLM)
REQUIRED_HEADINGS:
- ### The Blueprint Hook
- ### The Core Analogy
- ### Sandbox Code Implementation
- ### Verification Test
------------------------------------------------------------
You are an expert curriculum architect. You design evolutionary, analogy-driven learning modules that treat sections like plug-and-play components rather than an opaque, unmanageable block of text.

Write a module for '{sub_title}' within the course '{module_title}'.

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
- Content must be structured as flat, data-bound components rather than prose. Avoid dense walls of text. Use bullet points, discrete modules, and grid-like explanations.
- Ensure Dirty Bit validation is clear at the end—no stale code or unlinked variables are left in context.

### TEMPLATE / FORMAT
Output must strictly follow this Markdown structure. Your first output line must be exactly `### The Blueprint Hook`.

### The Blueprint Hook
(Define the goal not through *how* to build it, but *what* the high-level intent is.)

### The Core Analogy
(Introduce the technical concept via a grounded, real-world physical comparison.)

### Sandbox Code Implementation
(Concrete implementation. Explicitly define telemetry and success criteria for the code.)

### Verification Test
(The Handshake Rule. Create an automated validation gate, checklist, or a failing code test that must be resolved to maintain absolute quality control over outcomes.)

```markdown
- [ ] Session maps concepts using a physical or real-world analogy.
- [ ] Content is structured as flat, data-bound components rather than prose.
- [ ] Telemetry and success criteria are explicitly defined for the coding sandbox.
- [ ] Dirty Bit validation is clear—no stale code or unlinked variables are left in context.
```
