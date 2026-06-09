# 01 - Product Vision

## One-liner
StudyLab is a NotebookLM-inspired AI study workspace for AI, data science, analytics, and finance learners. Students create notebooks, upload course sources, ask source-grounded questions with citations, solve checkable problems with verification, and export study artifacts such as summary notes, planners, timetables, and revision cards to Notion.

## Who it is for
- AI, ML, and data science learners.
- Analytics students learning statistics, SQL, BI, and experimentation.
- Finance students learning valuation, markets, ratios, and quantitative methods.

## Problem
- Generic chatbots do not reliably teach from the student's own material.
- Learners need exact citations back to uploaded sources.
- Technical subjects need objective verification for code, math, statistics, and finance formulas.
- Students also need study artifacts: summaries, planners, timetables, and revision cards.

## What we build
- **Notebook-based RAG**: each user creates source notebooks, uploads material, and asks within that notebook.
- **Source guides**: each uploaded source gets a summary, key concepts, and suggested questions.
- **Hybrid retrieval**: dense semantic search + sparse keyword/formula search + reranking.
- **Strict citations**: grounded answers include source id, chunk index, offsets, snippets, and score.
- **Verified solving**: code execution, symbolic/numeric checks, and finance formula checks.
- **Reveal-ready solutions**: steps are stored once and revealed without re-solving.
- **Study artifacts**: summary notes, study guides, planners, timetables, and revision cards.
- **Notion export**: generated artifacts can become private Notion pages by default.

## Core differentiator
StudyLab is source-grounded like NotebookLM, but optimized for technical learning: it cites the student's material and verifies checkable answers instead of relying on model confidence.

## Constraints
- Never show a "verified" label without an objective passing check.
- Never present an answer as source-grounded when retrieval support is weak.
- Easy/medium solve target: p90 under 5s. Hard/tail target: p90 under 10s.
- Reveal follow-ups must read stored steps and avoid new model calls.

## Out of scope for now
- Native mobile apps.
- Scaling, pricing, margins, and GTM economics.
- Fully general subjects outside AI/data/analytics/finance.
- Multi-agent teaching.

## Success
- Create notebook -> upload source -> source guide generated.
- Ask notebook question -> answer includes strict citations.
- Weak retrieval -> system refuses grounded answer.
- Solve checkable math/finance/code item -> verified output.
- Generate summary/planner/timetable/revision artifact -> export to Notion.
