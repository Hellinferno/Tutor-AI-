# 09 - Engineering Scope Definition

## Phase 1 in scope
- Monorepo foundation, CI, local env, Docker Compose.
- Notebook creation and source upload.
- Text extraction path for notes/PDF-extracted text.
- Chunking with stable offsets.
- Source guide generation.
- Hybrid RAG: sparse + dense + rerank.
- Strict citations.
- Low-confidence rejection.
- Verified solver for symbolic/math and finance formula cases.
- Code-exec sandbox contract.
- OCR input contract.
- Stored step reveal.
- Study artifacts: summary notes, study guide, planner, timetable, revision cards.
- Notion export adapter with mock local mode.
- Teaching whiteboard sessions.
- Quiz generation from notebook sources or topic hints.
- Question paper generation.
- Verified answer keys.
- Auto-evaluation attempts and reports.

## Later phase scope
- Full PDF parser and slide parser.
- Websites, YouTube, audio, and Google Docs imports.
- Student mastery model and advanced spaced repetition.
- Voice STT/TTS.
- Full production auth and billing.
- Multi-agent teaching.

## Build vs buy
| Component | Decision | Notes |
|---|---|---|
| Vector DB | Qdrant | hybrid retrieval and payload filtering |
| Metadata DB | Postgres | notebooks, sources, citations, artifacts |
| Cache | Redis | solution cache and session scratch |
| Embeddings | adapter | local deterministic now; production provider later |
| Reranker | adapter | local reranker now; stronger reranker later |
| Frontier model | API | hard/non-verifiable tail only |
| Code sandbox | isolated service | no network, time/memory caps |
| Notion | API adapter | private pages by default |

## Risk register
| Risk | Mitigation |
|---|---|
| Weak retrieval hallucination | threshold + insufficient-source-support response |
| Formula/code terms missed by vector search | sparse retrieval plus reranking |
| False verified answer | hard gate false_verified_rate=0 |
| Citation mismatch | stable chunk offsets and source metadata |
| Notion not connected | explicit connection error and local mock mode |
