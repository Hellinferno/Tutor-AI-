# StudyLab Phase 0-2

NotebookLM-inspired AI study lab for AI, data science, analytics, and finance learners.

This repository implements the Phase 0-2 vertical slice:

- notebooks and source upload
- source guide generation
- hybrid source-grounded answers with citations
- verified solving for symbolic/math, finance formula, and sandboxed code-execution cases
- cacheable reveal-ready solution steps
- OCR adapter contract
- student-facing Notion artifact export
- teaching whiteboard sessions
- quiz generation with verified answer keys
- question paper generation with verified answer keys
- auto-evaluation attempts and reports
- durable SQLite persistence (opt-in) alongside the in-memory store
- runnable gateway, rag, and solver services with Dockerfiles and Compose
- a prompt template library with a loader
- CI, migrations, fixtures, and tests

## Local Verification

```powershell
python -m unittest discover tests
python packages/eval/run_eval.py   # solver gate: false_verified_rate must be 0
```

Web app build:

```powershell
cd apps/web; npm install; npm run build
```

## Local Development Shape

The Python core in `packages/studylab_core` is dependency-light so it can run before Postgres, Redis, Qdrant, and Notion are provisioned. Service wrappers and Docker Compose show the intended deployment shape.

### Persistence

By default the core uses an in-memory store (ideal for tests and ephemeral runs). Set `STUDYLAB_SQLITE_PATH` to enable durable SQLite persistence that survives restarts:

```powershell
$env:STUDYLAB_SQLITE_PATH = "data/studylab.db"
python -m services.gateway.app.main
```

Postgres remains the production target; the SQLite store mirrors the same SQL contract as the migrations in `packages/db/migrations`.

### Services

Three runnable services share the env-selected store (over a shared volume in Compose):

- `gateway` (`PORT`, default 8000) — full surface
- `rag` (`RAG_PORT`, default 8001) — notebooks, sources, ask, artifacts
- `solver` (`SOLVER_PORT`, default 8002) — solve and reveal

```powershell
docker compose -f infra/compose/docker-compose.yml up --build
```

### Code-execution sandbox

The solver's `code_exec` path runs snippets in an isolated subprocess (`python -I -S`) after an AST allowlist check (only safe stdlib modules; no filesystem/network/import escapes). Output is captured as the verified answer; rejected or failing code is returned `unverified`.

### Prompts

Prompt templates live in `packages/prompts` (indexed by `registry.json`) and are loaded via `studylab_core.load_prompt` / `render_prompt`. Override the directory with `STUDYLAB_PROMPTS_DIR`.

Set `NOTION_MOCK_EXPORT=true` for local Notion export demos. Set `NOTION_API_KEY` to use the real Notion API.

## Phase 2 Learning Surfaces

Phase 2 adds deterministic local engines for teaching, quizzes, papers, answer keys, attempts, and reports. Answer keys include `verified` and `verification_method` metadata so the product can distinguish checked keys from draft content.

## RAG Architecture

Phase 1 uses a local dependency-free implementation of the production retrieval plan:

1. sparse keyword scoring for exact terms, formulas, tickers, function names, and definitions
2. dense semantic scoring through an embedding provider interface
3. reranking over the candidate chunks
4. strict citation output with source id, chunk index, character offsets, snippet, and score
5. low-confidence rejection instead of unsupported grounded answers

Production should swap the local retriever for Qdrant hybrid search:

- collection: `source_chunks`
- named vectors: `dense`, `sparse`, optional `late_interaction`
- required payload: `notebook_id`, `source_id`, `source_title`, `chunk_index`, `start_char`, `end_char`, `text`
- retrieval: metadata filter by notebook, prefetch dense + sparse candidates, rerank to the final evidence set
# Tutor-AI-
