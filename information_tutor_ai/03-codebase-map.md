# 03 — Codebase Map 🔵

Every folder and notable file in the repository, with one‑line descriptions. This mirrors the
**current** tree.

> 🟢 **Non‑developer tip:** think of this as the building directory in a lobby — "what's on each
> floor." You don't need to read the code; the descriptions tell you what each part is *for*.

---

## Top level

```
tutor AI/
├── apps/                  Front-end applications
├── services/             Backend HTTP services (gateway, rag, solver)
├── packages/             Shared libraries (engine, db, eval, prompts, types)
├── infra/                Docker + compose (how it's packaged & run)
├── data/                 Seed data (concept bank, fixtures)
├── docs/                 OpenAPI spec + RAG architecture notes
├── tests/                Python test suite (the quality gate)
├── Instructions/         The original product & engineering specs (source of truth for intent)
├── information_tutor_ai/ ← YOU ARE HERE: the human-readable project hub
├── .circleci/            CI pipeline definition
├── .env.example          All environment variables, documented
├── package.json          JS workspace root
├── pnpm-workspace.yaml   Declares the pnpm monorepo packages
├── turbo.json            Turborepo task config
├── pyproject.toml        Python project + test config
└── README.md             Repo-level readme
```

---

## `apps/web/` — the website (Next.js 15 / React 19)

| File | What it is |
|---|---|
| `app/layout.tsx`, `app/page.tsx`, `app/styles.css` | The Next.js app router root, main page, styles. |
| `components/notebook-chat.tsx` | The grounded Q&A chat panel. |
| `components/solve-panel.tsx` | The solve/verify panel. |
| `components/source-panel.tsx` | Upload & list sources. |
| `components/artifact-panel.tsx` | Generate & view study artifacts. |
| `lib/api.ts` | Client calls to the backend. |
| `package.json` | Scripts: `build` (`next build`), `dev`, `lint`, `typecheck`. |
| `preview.html` | Static preview. |

> Build is verified: `npm install && npm run build` compiles, type‑checks, and prerenders.
> `node_modules/` and `.next/` are git‑ignored.

---

## `services/` — backend HTTP services

Each service is a thin entrypoint over `studylab_core`. They share the env‑selected store.

| File | Service | Port (env) | Routes |
|---|---|---|---|
| `gateway/app/main.py` | **gateway** | 8000 (`PORT`) | Full API (notebooks, sources, ask, solve, reveal, artifacts, notion). |
| `rag/app/main.py` | **rag** | 8001 (`RAG_PORT`) | notebooks, sources upload/get, ask, artifacts generate. |
| `solver/app/main.py` | **solver** | 8002 (`SOLVER_PORT`) | solve, reveal. |

Each also keeps a small factory (`create_rag_engine`, `create_solver_engine`) for embedding the
engine in tests/other code. All expose `GET /health`.

---

## `packages/studylab_core/studylab_core/` — the engine

| File | Responsibility |
|---|---|
| `__init__.py` | Public exports (`StudyLabAPI`, stores, engines, prompt loaders, `make_store_from_env`). |
| `api.py` | `StudyLabAPI` façade — the method surface every service calls. |
| `models.py` | Dataclasses: `Notebook`, `Source`, `SourceChunk`, `SourceGuide`, `Citation`, `Solution`, `Artifact`, responses; the `VerifyMethod`/`GroundingState`/`ArtifactType` literals. |
| `store.py` | `InMemoryStudyLabStore` — default ephemeral store. |
| `store_sqlite.py` | `SqliteStudyLabStore` — durable store with identical surface; `make_store_from_env`. |
| `rag.py` | `RagEngine` — ingest, retrieve, `ask` (grounded answer or refusal). |
| `retrieval.py` | `HybridRetriever` (sparse+dense+rerank), embedding provider interface, `QdrantHybridSearchAdapter`. |
| `text_processing.py` | Chunking with offsets, source‑guide generation, citation building, sentence selection, tokeniser. |
| `solver.py` | `SolverEngine` — symbolic, finance NPV, code‑exec routing; caching; reveal. |
| `sandbox.py` | Code extraction, AST allowlist validation, isolated subprocess runner. |
| `artifacts.py` | `ArtifactGenerator` — the five artifact renderers. |
| `notion.py` | `NotionExporter` — real Notion API + mock; Markdown→blocks. |
| `prompts.py` | `load_prompt` / `render_prompt` / `list_prompts` over the registry. |
| `service_http.py` | Minimal reusable HTTP router (`Route`, `serve`) used by rag/solver. |

---

## `packages/` — other shared libraries

| Path | What it holds |
|---|---|
| `db/migrations/001_phase1_foundation.sql` | Postgres schema: users, notebooks, sources, source_chunks, source_guides, questions, solutions, artifacts, sessions, revision_cards + indexes & enums. |
| `eval/run_eval.py` | The solver quality gate (asserts `false_verified_rate == 0`). |
| `eval/benchmarks/phase1_solver.json` | 15 benchmark cases (symbolic / formula / code_exec). |
| `prompts/registry.json` + `*.md` | Prompt templates: source_guide, notebook_answer, solver_system, artifact_summary_notes, artifact_study_guide. |
| `shared-types/src/index.ts` | TypeScript interfaces mirroring the Python models. |

---

## `infra/` — packaging & running

| Path | What it is |
|---|---|
| `compose/docker-compose.yml` | postgres, redis, qdrant, gateway, rag, solver + a shared `studylab_data` volume for the SQLite DB. |
| `docker/gateway.Dockerfile` | Builds the gateway image (ships core + prompts). |
| `docker/rag.Dockerfile` | Builds the rag image. |
| `docker/solver.Dockerfile` | Builds the solver image. |

---

## `data/`, `docs/`, `tests/`, `Instructions/`

| Path | What it is |
|---|---|
| `data/concept-bank/phase1.json` | Subject → key concepts seed list. |
| `data/fixtures/sample_notes.md` | Sample source text for demos/tests. |
| `docs/openapi.phase1.yml` | OpenAPI description of the Phase 1 API. |
| `docs/rag-architecture.md` | Retrieval design notes. |
| `tests/test_phase1_core.py` | 12 tests: chunking, grounded ask, refusal, retrieval ranking, solver, reveal, artifacts, OCR. |
| `tests/test_phase1_infra.py` | 12 tests: SQLite persistence, sandbox, prompts, service router, OCR path. |
| `Instructions/01..12 + design docs` | The original product/engineering specifications (intent & gates). |
