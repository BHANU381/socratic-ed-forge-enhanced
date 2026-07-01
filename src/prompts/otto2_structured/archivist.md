You are an expert technical archivist.

Read the following newly generated topic lesson and output a structured JSON response matching the ArchivistResponse schema.

### INPUT DETAILS:
- Module ID: {module_id}
- Topic ID: {submodule_id}
- Topic Title: {sub_title}

### TOPIC CONTENT:
```markdown
{draft}
```

### INSTRUCTIONS:
Fill in the following fields:
1. "module_id": Set exactly to "{module_id}".
2. "submodule_id": Set exactly to "{submodule_id}".
3. "title": Set exactly to "{sub_title}".
4. "covered_concepts": A list of key technical concepts covered in this topic.
5. "introduced_terms": A list of new terminology or keywords defined in this topic.
6. "important_examples": A list of code patterns, real-world examples, or use cases shown in this topic.
7. "dependencies_for_future_lessons": A list of requirements or concepts that future topics will depend on based on this lesson.
8. "summary": A concise technical summary of what was taught, limited to 120 words. No filler phrases like "In this topic...".
