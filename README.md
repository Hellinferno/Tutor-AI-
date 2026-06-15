# StudyLab Phase 0-7

NotebookLM-inspired AI study lab for AI, data science, analytics, and finance learners.

This repository implements the Phase 0-7 vertical slice (151 tests, `false_verified_rate=0`):

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
- spaced-repetition revision (SM-2), per-topic mastery, progress analytics, voice I/O
- **Phase 4** source connectors (website / YouTube / audio / Google Doc / Slides)
- **Phase 4** multi-agent teaching (explainer / grounding-verifier / practice-coach turns)
- **Phase 4** pricing & economics (Free/Scholar/Pro plans, usage metering, quota checks, Stripe seam)
- **Phase 5** auth & observability: email/password auth (PBKDF2 + stateless HS256 JWT), per-user authorization, env-gated quota enforcement (HTTP 402), and a `/metrics` observability endpoint
- **Phase 6** production hardening + user readiness: per-user ownership (IDOR-safe), CORS, rate limiting (HTTP 429), input-size caps, `/ready`, account self-service (change/reset password, edit profile, delete account + cascade), and one-click sample onboarding
- **Phase 7** collaboration: notebook sharing (viewer/editor), "shared with me", share-aware authorization, and student/instructor/admin roles with admin-only routes
- durable SQLite persistence (opt-in) alongside the in-memory store
- runnable gateway, rag, and solver services with Dockerfiles and Compose
- an interactive, responsive Next.js web app (17 panels) wired to the gateway
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

## Learning surfaces (Phase 2-4)

Phase 2 adds deterministic local engines for teaching, quizzes, papers, answer keys, attempts, and reports. Answer keys include `verified` and `verification_method` metadata so the product can distinguish checked keys from draft content.

Phase 3 adds spaced-repetition revision (SM-2), a per-topic student mastery model, progress analytics, and an env-gated voice provider (mock by default, Gemini with `GEMINI_API_KEY`).

Phase 4 adds source connectors (website / YouTube / audio / Google Doc / Slides — content is chunked and cited exactly like an upload), multi-agent teaching (explainer / grounding-verifier / practice-coach turns per concept), and a pricing layer (Free/Scholar/Pro plans, usage metering, quota checks). Billing runs through a mock provider by default and a real Stripe Checkout seam with `STRIPE_API_KEY`.

Phase 5 adds auth & observability: first-party email/password auth (PBKDF2-HMAC-SHA256 hashing, stateless HS256 JWTs — stdlib only), per-user authorization (notebook ownership), quota enforcement (over-limit metered actions return HTTP 402), and an in-process `/metrics` observability endpoint.

Phase 6 adds production hardening + user readiness: the gateway derives identity from the bearer token and enforces per-user ownership (IDOR-safe), with CORS + preflight, sliding-window rate limiting (HTTP 429), source input-size caps, a `/ready` probe, and a fail-fast JWT secret. Users get full account self-service — change/reset password, edit profile, and delete their account (cascading all their data) — plus one-click "Load sample" onboarding. Auth, quota, and rate-limit enforcement are gated behind env flags (`STUDYLAB_REQUIRE_AUTH` / `STUDYLAB_ENFORCE_QUOTAS` / `STUDYLAB_RATE_LIMIT`), off by default, so the app stays runnable offline.

Phase 7 adds collaboration: an owner can share a notebook with another user as a viewer (read / ask / generate) or editor (also add/modify sources); `authorize_notebook` honors shares so every notebook-scoped route works for collaborators, and a "shared with me" view lists notebooks others shared with you. Users carry a role (student / instructor / admin); admin is granted via `STUDYLAB_ADMIN_EMAILS` and gates `/v1/admin/*` (users overview + metrics). The full surface is documented in `docs/openapi.phase1.yml` and `information_tutor_ai/`.

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
