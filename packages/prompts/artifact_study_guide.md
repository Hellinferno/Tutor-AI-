# Study Guide

Render a study guide for the notebook "{{notebook_title}}".

Inputs:
- Key concepts: {{concepts}}

Output a Markdown document with:
- `# Study Guide for {{notebook_title}}`
- `## Concepts to Master` — one bullet per concept.
- `## Practice Prompts` — for the first 6 concepts, "Explain {concept} with one formula or example."

Every practice prompt must be answerable from the notebook's sources or by a verified solve.
