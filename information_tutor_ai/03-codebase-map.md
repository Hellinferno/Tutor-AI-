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

All panels are **interactive client components** (`"use client"`, React state, calling `lib/api.ts`)
— not static mockups.

| File | What it is |
|---|---|
| `app/layout.tsx`, `app/page.tsx`, `app/styles.css` | App router root; main page (wraps the 16 panels in `NotebookProvider` + a notebook bar); responsive/mobile styles. |
| `lib/api.ts` | Typed client for every gateway endpoint (Phase 1–6, incl. account self‑service) with an `ApiError` type + bearer‑token handling (`setAuthToken`/`loadAuthToken`). |
| `lib/types.ts` | Response interfaces mirroring the Python models / shared types. |
| `lib/notebook-context.tsx` | `NotebookProvider` / `useNotebook` — shares the active notebook id, last attempt id, and **signed‑in user id/email** across panels. |
| `components/notebook-bar.tsx` | Create / show the active notebook (header); **Phase 6** one-click "Load sample" onboarding. |
| `components/auth-panel.tsx` | **Phase 5–6** — register / sign in / sign out; **Phase 6** account self-service (change/reset password, edit subject, delete account). |
| `components/source-panel.tsx` | Upload sources, render the generated source guide. |
| `components/connectors-panel.tsx` | **Phase 4** — import website / YouTube / audio / Google Doc / Slides; lists imports. |
| `components/notebook-chat.tsx` | Grounded Q&A with citations, grounding badge, clickable follow-ups. |
| `components/teaching-panel.tsx` | **Phase 2** — whiteboard session with Prev/Next concept nav. |
| `components/multi-agent-panel.tsx` | **Phase 4** — explainer / verifier / coach turns per concept. |
| `components/solve-panel.tsx` | Verified solve + progressive step reveal. |
| `components/quiz-panel.tsx` | **Phase 2** — generate, answer, submit, per-question scoring. |
| `components/paper-panel.tsx` | **Phase 2** — sectioned paper, answer, submit. |
| `components/artifact-panel.tsx` | Generate & render the five study artifacts. |
| `components/report-panel.tsx` | **Phase 2** — loads the eval report for the last attempt. |
| `components/revision-panel.tsx` | **Phase 3** — generate cards, due queue, Forgot/Recalled, live stats. |
| `components/analytics-panel.tsx` | **Phase 3** — mastery, score-trend chart, user summary. |
| `components/voice-panel.tsx` | **Phase 3** — STT/TTS via the voice provider. |
| `components/pricing-panel.tsx` | **Phase 4** — plan catalog, switch plan, live usage/quota meter. |
| `components/metrics-panel.tsx` | **Phase 5** — live observability snapshot from `/metrics`. |
| `package.json` | Scripts: `build` (`next build`), `dev`, `lint`, `typecheck`. |
| `preview.html` | Static preview. |

> Build is verified: `npm install && npm run build` compiles, type‑checks, and prerenders.
> `node_modules/` and `.next/` are git‑ignored.

---

## `services/` — backend HTTP services

Each service is a thin entrypoint over `studylab_core`. They share the env‑selected store.

| File | Service | Port (env) | Routes |
|---|---|---|---|
| `gateway/app/main.py` | **gateway** | 8000 (`PORT`) | Full API: Phase 1–4 routes, auth/`/metrics` + bearer enforcement & quota 402 (Phase 5), **account self‑service + IDOR‑safe per‑user ownership, CORS, rate‑limit 429, input caps, `/ready` (Phase 6)**. |
| `rag/app/main.py` | **rag** | 8001 (`RAG_PORT`) | Internal mirror of the Phase 1–5 route table; **Phase 6** binds loopback (`RAG_BIND_HOST`) — runs behind the authenticated gateway. |
| `solver/app/main.py` | **solver** | 8002 (`SOLVER_PORT`) | solve, reveal. |

Each also keeps a small factory (`create_rag_engine`, `create_solver_engine`) for embedding the
engine in tests/other code. All expose `GET /health`.

---

## `packages/studylab_core/studylab_core/` — the engine

| File | Responsibility |
|---|---|
| `__init__.py` | Public exports (`StudyLabAPI`, stores, engines, prompt loaders, `make_store_from_env`). |
| `api.py` | `StudyLabAPI` façade — the method surface every service calls. |
| `models.py` | Dataclasses for all phases: Phase 1 (`Notebook`, `Source`, `SourceChunk`, `SourceGuide`, `Citation`, `Solution`, `Artifact`, responses); **Phase 2** (`WhiteboardConcept`/`WhiteboardSession`, `QuizQuestion`/`Quiz`, `PaperSection`/`QuestionPaper`, `Attempt`, `AnswerKey`, `EvalReport`); **Phase 3** (`RevisionCard`, `Session`, `StudentProfile`, `TopicMastery`, `KnowledgeState`, `VoiceResult`); **Phase 4** (`SourceImport`, `AgentTurn`/`MultiAgentTeachingSession`, `Plan`, `Subscription`, `UsageRecord`); **Phase 5** (`User`); plus the `VerifyMethod`/`GroundingState`/`ArtifactType`/`QuestionType`/`AttemptSourceType`/`Difficulty`/`ConnectorType`/`PlanTier`/`MeteredAction` literals. |
| `store.py` | `InMemoryStudyLabStore` — default ephemeral store (Phase 1–6 collections incl. users; `delete_user` cascade). |
| `store_sqlite.py` | `SqliteStudyLabStore` — durable store with identical surface (Phase 1–6 tables incl. users; `save_user`/`delete_user`); `make_store_from_env`. |
| `connectors.py` | **Phase 4** — `SourceConnectorEngine`: validates/normalizes website/YouTube/audio/Doc/Slides payloads, then chunks + guides + cites via `RagEngine`. |
| `pricing.py` | **Phase 4** — `PricingEngine` (plan catalog, subscriptions, usage metering, quota checks) + `BillingProvider` (`MockBillingProvider` / `StripeBillingProvider`); `make_billing_provider`. **Phase 5** adds `enforce` + `QuotaExceededError`. |
| `auth.py` | **Phase 5–6** — `AuthEngine`: register/login, PBKDF2 hashing, stdlib HS256 JWT (purpose‑scoped); **Phase 6** account self‑service (change/reset password, update profile, delete account); `make_auth_secret` fails fast on the dev secret when auth is enforced; `AuthError`. |
| `metrics.py` | **Phase 5** — `MetricsCollector`: thread‑safe in‑process counters for the spec's observability signals (refusal rate, citation coverage, verified rate, cache hit, solve latency). |
| `ratelimit.py` | **Phase 6** — `RateLimiter` (in‑memory sliding window) + `make_rate_limiter_from_env`; `RateLimitError` (→ HTTP 429). |
| `rag.py` | `RagEngine` — ingest, retrieve, `ask` (grounded answer or refusal). |
| `retrieval.py` | `HybridRetriever` (sparse+dense+rerank), embedding provider interface, `QdrantHybridSearchAdapter`. |
| `text_processing.py` | Chunking with offsets, source‑guide generation, citation building, sentence selection, tokeniser. |
| `solver.py` | `SolverEngine` — symbolic, finance NPV, code‑exec routing; caching; reveal. |
| `sandbox.py` | Code extraction, AST allowlist validation, isolated subprocess runner. |
| `artifacts.py` | `ArtifactGenerator` — the five artifact renderers. |
| `teaching.py` | **Phase 2 + 4** — `TeachingEngine`: cited whiteboard concept progression; **Phase 4** adds the multi‑agent session (explainer / grounding‑verifier / practice‑coach turns per concept). |
| `quiz.py` | **Phase 2** — `QuizEngine`: generates MCQ/true‑false/short‑answer questions from sources or a topic; verified answer keys. |
| `paper.py` | **Phase 2** — `PaperEngine`: assembles sectioned question papers (reusing `QuizEngine`); marks + duration. |
| `eval.py` | **Phase 2** — `EvalEngine`: grades attempts deterministically and builds reports (percentage, weak/strong topics, summary). |
| `revision.py` | **Phase 3** — `RepetitionEngine`: SM‑2 revision cards (generate, due queue, review/reschedule, stats). |
| `student.py` | **Phase 3** — `StudentModel`: per‑topic mastery + knowledge state from eval reports. |
| `analytics.py` | **Phase 3** — `AnalyticsEngine`: notebook score trends + user summary. |
| `voice.py` | **Phase 3** — `VoiceProvider` (STT/TTS): `MockVoiceProvider` + `GeminiVoiceProvider`; `make_voice_provider`. |
| `notion.py` | `NotionExporter` — real Notion API + mock; Markdown→blocks. |
| `prompts.py` | `load_prompt` / `render_prompt` / `list_prompts` over the registry. |
| `service_http.py` | Minimal reusable HTTP router (`Route`, `serve`) used by rag/solver. |

---

## `packages/` — other shared libraries

| Path | What it holds |
|---|---|
| `db/migrations/001_phase1_foundation.sql` | Postgres schema: users, notebooks, sources, source_chunks, source_guides, questions, solutions, artifacts, sessions, revision_cards + indexes & enums. |
| `db/migrations/002_phase2_teaching_quiz.sql` | **Phase 2** Postgres schema: whiteboard_sessions, quizzes, quiz_questions, question_papers, paper_sections, attempts, answer_keys, eval_reports + indexes & enums. |
| `db/migrations/003_phase3_revision_voice.sql` | **Phase 3** Postgres schema: revision_cards (SM‑2 columns), sessions (kind), student_profiles, topic_masteries + indexes. |
| `db/migrations/004_phase4_connectors_agents_billing.sql` | **Phase 4** Postgres schema: source_imports, multi_agent_teaching_sessions, subscriptions, usage_records + indexes. |
| `db/migrations/005_phase5_auth_observability.sql` | **Phase 5** Postgres schema: `users.password_hash` + email/notebook‑owner indexes (JWT is stateless; metrics are in‑process). |
| `db/migrations/006_phase6_hardening.sql` | **Phase 6** — no new tables (hardening is app‑layer; account deletion cascades existing tables); adds supporting indexes. |
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
| `docs/openapi.phase1.yml` | OpenAPI description of the API (Phase 0–6; title "StudyLab Phase 0-6 API"). |
| `docs/rag-architecture.md` | Retrieval design notes. |
| `tests/test_phase1_core.py` | 12 tests: chunking, grounded ask, refusal, retrieval ranking, solver, reveal, artifacts, OCR. |
| `tests/test_phase1_infra.py` | 12 tests: SQLite persistence, sandbox, prompts, service router, OCR path. |
| `tests/test_phase2_core.py` | 20 tests: teaching, quizzes, papers, verified keys, auto-eval, edge cases. |
| `tests/test_phase3_core.py` | 20 tests: revision/SM-2, student mastery, analytics, voice. |
| `tests/test_phase4_core.py` | 23 tests: connectors (validation, HTML strip, metering), multi-agent teaching, pricing/quotas, SQLite persistence. |
| `tests/test_phase5_core.py` | 20 tests: password hashing, auth (register/login/JWT verify/expiry/tamper), authorization (ownership), quota enforcement, observability metrics. |
| `tests/test_phase6_core.py` | 23 tests: account self-service (change/reset/profile/delete cascade incl. grading artifacts), input caps, rate limiter, JWT-secret guard, reset-token gating, malformed-token → AuthError. |
| `Instructions/01..12 + design docs` | The original product/engineering specifications (intent & gates). |
