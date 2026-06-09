# 10 - Development Phases

Build-focused. Scaling and economics are excluded.

## Phase 0 - Foundations
- Monorepo, CI, local env, Docker Compose.
- DB migrations for notebooks, sources, chunks, guides, questions, solutions, artifacts.
- Gateway skeleton and shared API contracts.
- Eval harness and seed benchmark.

## Phase 1 - Notebook RAG + verified solver
- Notebook creation.
- Source upload and source guides.
- Chunking with offsets.
- Hybrid retrieval: sparse + dense + rerank.
- Strict source citations.
- Low-confidence rejection.
- Text solve and OCR solve contract.
- Verified solver for symbolic/math and finance formula cases.
- Cache and stored step reveal.
- Artifact generation: summary notes, study guide, planner, timetable, revision cards.
- Notion export adapter.

**Gate:** tests pass, solver eval false_verified_rate=0, cited answers include source metadata, weak retrieval refuses grounding.

## Phase 2 - Teaching, quizzes, and papers
- Teaching engine with whiteboard.
- Quiz generation from notebook or topic.
- Question paper generation from notebook or topic.
- Verified answer keys.
- Auto-eval and reports.

## Phase 3 - Memory, revision, analytics, voice
- Student model.
- Spaced repetition schedule.
- Progress analytics.
- Voice input/output.
- Weak-topic revision cards.

## Phase 4 - Later
- Multi-agent teaching.
- Mobile.
- Scaling, pricing, and economics.
- More source connectors: websites, YouTube, audio, Google Docs/Slides.

## Sequencing rationale
Notebook-grounded RAG and verification are the product's foundation. Quizzes, papers, and memory should reuse the same citation and verification engines instead of building separate flows.
