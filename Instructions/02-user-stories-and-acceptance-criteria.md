# 02 - User Stories and Acceptance Criteria

## Personas
- **Dia, DS learner**: uploads ML notes and asks for explanations with citations.
- **Arun, analytics student**: practices statistics and wants formula/code checking.
- **Fiona, finance student**: solves valuation problems and exports revision plans.

## Epic 1: Notebook and source management
- US1.1: Create a study notebook for a course or topic.
  - AC: Notebook has id, title, user id, and source list.
- US1.2: Upload notes, PDF-extracted text, slides text, or pasted material.
  - AC: Source is stored, chunked with stable offsets, and marked ready.
- US1.3: View a source guide.
  - AC: Guide includes summary, key concepts, and suggested questions.

## Epic 2: Source-grounded RAG
- US2.1: Ask a notebook question.
  - AC: System retrieves only within selected notebook by default.
  - AC: Answer includes citations with source id, source title, chunk index, offsets, snippet, and score.
- US2.2: Ask something unsupported by sources.
  - AC: System returns insufficient-source-support and does not fake grounding.
- US2.3: Ask exact technical questions with formulas or code terms.
  - AC: Sparse keyword/formula retrieval participates with dense retrieval and reranking.

## Epic 3: Verified solving
- US3.1: Paste a math, stats, code, or finance problem.
  - AC: Solver normalizes and hashes the problem, checks cache, solves, and verifies where possible.
  - AC: Math/stats use symbolic or numeric checks.
  - AC: Finance uses formula evaluation for NPV, IRR, TVM, ratios, and later options.
  - AC: Code routes to isolated sandbox execution.
- US3.2: Reveal steps.
  - AC: Reveal endpoint returns stored steps only and performs no new solve.

## Epic 4: Study artifacts
- US4.1: Generate summary notes from a notebook.
  - AC: Artifact is derived from source guides and cited chunks.
- US4.2: Generate planner, timetable, and revision cards.
  - AC: Artifact uses notebook concepts and can be exported.
- US4.3: Export artifact to Notion.
  - AC: Private Notion page is default.
  - AC: If Notion is not connected, error explains how to connect or use mock export.

## Epic 5: Later learning workflows
- US5.1: Generate live quizzes from material or topic.
- US5.2: Generate full question papers from material or topic.
- US5.3: Track mastery and schedule spaced repetition.

## Global acceptance gates
- No false verified answers.
- No source-grounded answer without citations.
- Weak retrieval must refuse grounding.
- Notion export must not silently fail.
