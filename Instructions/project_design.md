# Project Design

## Summary
StudyLab is a source-grounded technical study workspace. The first product surface is a NotebookLM-inspired notebook: upload sources, inspect source guides, ask grounded questions with citations, solve checkable problems, generate study artifacts, and export them to Notion.

## Design goals
- Make uploaded sources the center of the experience.
- Show citation evidence clearly.
- Refuse unsupported grounded answers.
- Verify technical answers when possible.
- Turn source material into usable study outputs: summaries, planners, timetables, revision cards.

## Key decisions
| Decision | Choice | Rationale |
|---|---|---|
| Primary UX | Notebook workspace | Familiar source-first model |
| RAG | Hybrid dense + sparse + rerank | Handles concepts plus exact formulas/code terms |
| Vector DB | Qdrant | Designed for vector payload filtering and hybrid patterns |
| Metadata DB | Postgres | Durable source/citation/artifact metadata |
| Verification | Objective checks | Prevents fake confidence |
| Notion | Export artifacts | Meets planner/timetable/notes workflow |
| Step reveal | Stored solution steps | No re-derivation |

## Current UI shape
- Left navigation: Sources, Ask, Solve, Artifacts.
- Source panel: uploaded material and source guide.
- Ask panel: cited notebook answer.
- Solve panel: verified answer and reveal action.
- Artifact panel: summary, study guide, planner, timetable, revision cards, Notion export.

## RAG behavior
- Search is scoped to notebook.
- Sparse retrieval catches exact technical terms.
- Dense retrieval catches paraphrases.
- Reranker chooses strongest evidence.
- Citations include snippet and chunk metadata.
- Weak evidence returns insufficient-source-support.

## Verification behavior
- Math/stats: symbolic/numeric.
- Finance: formula.
- Code: sandbox execution.
- Conceptual: cited but not verified unless cross-check passes.

## Deferred
- Full quiz and question paper workflows.
- Full mastery analytics.
- Voice.
- Native mobile.
- Multi-agent teaching.
