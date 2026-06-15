# 02 — Architecture 🔵

How the system is structured and how a request flows through it. Paired with a plain‑English
explainer at the top of each section.

---

## 1. High‑level shape

> 🟢 **In plain English:** A website talks to a "gateway" (front door). Behind it, one shared
> brain (`studylab_core`) does the real work — finding passages, writing grounded answers,
> solving and verifying problems, and remembering everything. Two extra service doors (`rag`,
> `solver`) expose slices of that same brain so the system can scale into separate processes
> later.

```
┌──────────────┐        HTTP/JSON         ┌─────────────────────────────────────┐
│  Web (Next)  │ ───────────────────────▶ │  gateway  (services/gateway)        │
│  apps/web    │                          │  full API surface                   │
└──────────────┘                          └───────────────┬─────────────────────┘
                                                           │ imports
                          ┌────────────────────────────────▼────────────────────┐
                          │  studylab_core  (packages/studylab_core)             │
                          │  ─ the shared engine used by every service ─         │
                          │                                                      │
                          │  StudyLabAPI ── RagEngine ── HybridRetriever         │
                          │       │           │                                 │
                          │       │           └─ text_processing (chunk/guide)  │
                          │       ├─ SolverEngine ── sandbox (code exec)        │
                          │       ├─ ArtifactGenerator                          │
                          │       ├─ TeachingEngine · QuizEngine (Phase 2)      │
                          │       ├─ PaperEngine · EvalEngine   (Phase 2)       │
                          │       ├─ RepetitionEngine · StudentModel (Phase 3)  │
                          │       ├─ AnalyticsEngine · VoiceProvider (Phase 3)  │
                          │       ├─ SourceConnectorEngine      (Phase 4)       │
                          │       ├─ PricingEngine · BillingProvider (Phase 4)  │
                          │       ├─ AuthEngine · MetricsCollector  (Phase 5)   │
                          │       ├─ RateLimiter (gateway)         (Phase 6)   │
                          │       ├─ NotionExporter                             │
                          │       └─ Store (InMemory │ SQLite)                  │
                          └──────────────────────────────────────────────────────┘
                          ▲                              ▲
        same engine, slices exposed as services         │ env-selected store
                          │                              │
        ┌─────────────────┴────────┐      ┌──────────────┴───────────────┐
        │  rag    (services/rag)   │      │  solver (services/solver)    │
        │  notebooks/sources/ask/  │      │  solve / reveal              │
        │  artifacts               │      │                              │
        └──────────────────────────┘      └──────────────────────────────┘

  Infra (docker-compose): postgres · redis · qdrant · gateway · rag · solver · shared volume
```

---

## 2. Components

| Component | Path | Role |
|---|---|---|
| **Web app** | [apps/web](../apps/web) | Next.js 15 / React 19 UI — 17 **interactive, responsive** panels (account, sharing, sources, connectors, ask, teach, multi‑agent, solve, quiz, paper, artifacts, report, revision, analytics, voice, plans, metrics) wired to the gateway via [lib/api.ts](../apps/web/lib/api.ts) and a shared [NotebookProvider](../apps/web/lib/notebook-context.tsx). |
| **Gateway service** | [services/gateway](../services/gateway) | HTTP front door exposing the full API (Phase 1–7). Maps engine errors to status codes (401/402/403/404/400/429) and, when `STUDYLAB_REQUIRE_AUTH` is set, enforces a bearer token + per‑user ownership (honoring shares). Uses the env‑selected store. |
| **RAG service** | [services/rag](../services/rag) | Internal HTTP service mirroring the Phase 1–5 route table via a clean `Route` list; **Phase 6** binds loopback (`RAG_BIND_HOST`) and runs behind the authenticated gateway (no auth of its own). |
| **Solver service** | [services/solver](../services/solver) | Standalone HTTP service for solve/reveal routes. |
| **Core engine** | [packages/studylab_core](../packages/studylab_core) | The dependency‑light brain shared by all services. |
| **DB migrations** | [packages/db](../packages/db) | Postgres schema (production target). |
| **Eval harness** | [packages/eval](../packages/eval) | The solver quality gate + benchmark. |
| **Prompts** | [packages/prompts](../packages/prompts) | Prompt templates + registry, loaded at runtime. |
| **Shared types** | [packages/shared-types](../packages/shared-types) | TypeScript interfaces shared with the web app. |

> 🟢 **Why three services that share one engine?** Today the gateway does everything in‑process
> (simplest, fastest to build). The `rag` and `solver` services expose the *same* engine over
> their own ports so that, when traffic grows, those workloads can be scaled and deployed
> independently without rewriting the logic.

---

## 3. The engine internals (`studylab_core`)

`StudyLabAPI` ([api.py](../packages/studylab_core/studylab_core/api.py)) is the façade. It wires
together:

- **RagEngine** ([rag.py](../packages/studylab_core/studylab_core/rag.py)) — ingests sources,
  retrieves evidence, and writes grounded answers or refuses.
- **HybridRetriever** ([retrieval.py](../packages/studylab_core/studylab_core/retrieval.py)) —
  sparse + dense + rerank scoring; plus a Qdrant payload/query‑plan adapter for production.
- **SolverEngine** ([solver.py](../packages/studylab_core/studylab_core/solver.py)) — symbolic
  math, finance NPV, and sandboxed code execution; caching and step reveal.
- **Sandbox** ([sandbox.py](../packages/studylab_core/studylab_core/sandbox.py)) — AST allowlist
  + isolated subprocess execution.
- **ArtifactGenerator** ([artifacts.py](../packages/studylab_core/studylab_core/artifacts.py)) —
  the five study artifacts.
- **TeachingEngine** ([teaching.py](../packages/studylab_core/studylab_core/teaching.py)) *(Phase 2)*
  — builds a cited whiteboard concept progression from source guides + chunks.
- **QuizEngine** ([quiz.py](../packages/studylab_core/studylab_core/quiz.py)) *(Phase 2)* —
  generates MCQ/true‑false/short‑answer questions (from sources or a topic) with verified keys.
- **PaperEngine** ([paper.py](../packages/studylab_core/studylab_core/paper.py)) *(Phase 2)* —
  assembles sectioned question papers (reusing `QuizEngine`) with marks + duration.
- **EvalEngine** ([eval.py](../packages/studylab_core/studylab_core/eval.py)) *(Phase 2)* — grades
  attempts deterministically and builds reports (percentage, weak/strong topics, summary).
- **RepetitionEngine** ([revision.py](../packages/studylab_core/studylab_core/revision.py)) *(Phase 3)*
  — generates revision cards from notebook concepts and reschedules them with an SM‑2 algorithm.
- **StudentModel** ([student.py](../packages/studylab_core/studylab_core/student.py)) *(Phase 3)* —
  derives per‑topic mastery from a user's eval reports; surfaces weak/strong topics.
- **AnalyticsEngine** ([analytics.py](../packages/studylab_core/studylab_core/analytics.py)) *(Phase 3)*
  — per‑attempt score trends and an overall user summary.
- **VoiceProvider** ([voice.py](../packages/studylab_core/studylab_core/voice.py)) *(Phase 3)* —
  STT/TTS behind an interface; `MockVoiceProvider` default, `GeminiVoiceProvider` when `GEMINI_API_KEY` is set.
- **SourceConnectorEngine** ([connectors.py](../packages/studylab_core/studylab_core/connectors.py)) *(Phase 4)*
  — validates/normalizes website/YouTube/audio/Doc/Slides payloads, then ingests them through
  `RagEngine` so chunking, guides, and citations are identical to an upload.
- **TeachingEngine (multi‑agent)** *(Phase 4)* — the same engine also builds a multi‑agent session:
  per concept, an explainer / grounding‑verifier / practice‑coach turn, each cited.
- **PricingEngine** ([pricing.py](../packages/studylab_core/studylab_core/pricing.py)) *(Phase 4–5)* —
  plan catalog, subscriptions, usage metering, and quota checks; payments behind a `BillingProvider`
  (`MockBillingProvider` default, `StripeBillingProvider` when `STRIPE_API_KEY` is set). Phase 5 adds
  `enforce` (raises `QuotaExceededError` → HTTP 402).
- **AuthEngine** ([auth.py](../packages/studylab_core/studylab_core/auth.py)) *(Phase 5)* —
  email/password registration & login; PBKDF2‑HMAC‑SHA256 password hashing and stateless HS256 JWTs
  (stdlib only, no external dependency); ownership checks back per‑user authorization.
- **MetricsCollector** ([metrics.py](../packages/studylab_core/studylab_core/metrics.py)) *(Phase 5)* —
  thread‑safe in‑process counters for the spec's observability signals, served at `/metrics`.
- **AuthEngine self-service + RateLimiter** *(Phase 6)* — `auth.py` adds change/reset password,
  update profile, and account deletion (cascade); [ratelimit.py](../packages/studylab_core/studylab_core/ratelimit.py)
  is a sliding-window limiter the gateway applies (→ 429). The gateway derives the caller's identity
  from the bearer token and enforces per‑user **ownership** (no IDOR) plus CORS and input‑size caps.
- **Sharing & roles** *(Phase 7)* — `NotebookShare` + store methods let an owner share a notebook
  (`viewer`/`editor`); `authorize_notebook(require_edit=…)` now allows the owner **or** a shared user,
  so every notebook‑scoped route honors shares. Users carry a `role` (`student`/`instructor`/`admin`);
  admin is granted via `STUDYLAB_ADMIN_EMAILS` and gates `/v1/admin/*`.
- **NotionExporter** ([notion.py](../packages/studylab_core/studylab_core/notion.py)) — real
  Notion API call + a mock mode for local demos.
- **Store** — [InMemoryStudyLabStore](../packages/studylab_core/studylab_core/store.py) or
  [SqliteStudyLabStore](../packages/studylab_core/studylab_core/store_sqlite.py), chosen by env.
- **text_processing** ([text_processing.py](../packages/studylab_core/studylab_core/text_processing.py))
  — chunking with character offsets, source‑guide generation, sentence selection, citations.

---

## 4. Request flows

### A) "Ask my notebook a question"
> 🟢 Find the best passages from *your* sources, answer only from them, show citations — or
> refuse if support is weak.

1. `POST /v1/notebooks/{id}/ask` → `StudyLabAPI.ask_notebook`.
2. `RagEngine.retrieve` → `HybridRetriever.retrieve`: tokenise the query, score every chunk by
   **sparse** (keyword/TF‑IDF‑like), **dense** (embedding cosine), and **rerank** (phrase +
   proximity + formula bonuses); combine into a final score.
3. Keep chunks above `min_score`; if none qualify → return `grounding = "insufficient_source_support"`
   (the honest refusal). Otherwise build the answer with inline `[source, chunk N]` citations.

### B) "Solve and verify"
> 🟢 Compute the answer with a real checker; only call it *verified* if a checker confirmed it.

1. `POST /v1/solve` → `SolverEngine.solve`.
2. Cache check by normalised‑question hash → return cached if present.
3. Try, in order: **extractable code** → run in sandbox (`code_exec`); **finance NPV** formula
   (`formula`); **symbolic** arithmetic (`symbolic`). First objective success wins and is marked
   `verified`. If none apply → `unverified` (never falsely verified).
4. Store the solution with reveal‑ready steps; `POST /v1/solve/{id}/reveal` flips a step to
   revealed and persists it.

### C) "Generate an artifact + export to Notion"
1. `POST /v1/notebooks/{id}/artifacts/generate` → `ArtifactGenerator.generate` builds Markdown
   from the notebook's source guides + citations.
2. `POST /v1/notion/export` → `NotionExporter` (real API if `NOTION_API_KEY` set, else mock when
   `NOTION_MOCK_EXPORT=true`).

### D) "Quiz me, then grade my attempt" *(Phase 2)*
> 🟢 Build practice questions from *your* sources, hide the answers, grade what you submit, and
> report what to revise.

1. `POST /v1/notebooks/{id}/quizzes/generate` → `QuizEngine.generate_quiz` draws concepts from
   source guides + sentences from chunks (or a supplied `topic`) and emits typed questions with
   citations.
2. `GET /v1/quizzes/{id}` returns the **student view** (answers blanked); `POST …/answer-key`
   returns the **verified** key (each answer carries `verified` + `verification_method`).
3. `POST /v1/quizzes/{id}/attempt` → `EvalEngine.evaluate_attempt` scores each answer
   deterministically → an `attempt`.
4. `GET /v1/reports/{attempt_id}` → `EvalEngine.generate_report`: percentage, weak/strong topics,
   and a summary. Question papers (`PaperEngine`) follow the same generate → key → attempt → report
   path with `source_type = "paper"`. Teaching sessions use
   `POST /v1/notebooks/{id}/teaching/start` then `GET /v1/teaching/{id}` + `…/next` / `…/prev`.

### E) "Remember and revise" *(Phase 3)*
> 🟢 Turn what you've studied into scheduled flashcards, track which topics you've mastered, and
> chart your progress — all from your own attempt history.

1. `POST /v1/notebooks/{id}/revision/generate-cards` → `RepetitionEngine.generate_cards` makes
   cards from notebook concepts (or supplied topics). `GET /v1/revision/due` lists what's due;
   `POST /v1/revision/{card_id}/review` applies SM‑2 (easiness factor, interval, streak) and
   reschedules.
2. `POST /v1/student/{user_id}/mastery` → `StudentModel.compute_mastery` reads the user's eval
   reports to score each topic; `GET …/notebook/{id}/mastery` and `…/weak-topics` read it back.
3. `GET /v1/analytics/notebook/{id}/trends` and `/analytics/user/{user_id}/summary` →
   `AnalyticsEngine`. `POST /v1/voice/stt` / `…/tts` → `VoiceProvider` (mock unless `GEMINI_API_KEY`).

> 🟢 **Web flow:** every panel is a client component that calls `lib/api.ts`. A shared
> `NotebookProvider` holds the active notebook id and the last attempt id, so e.g. submitting a quiz
> lets the Reports panel load its evaluation.

### F) "Import a connector source, learn with a team, pick a plan" *(Phase 4)*
> 🟢 Bring in web/video/doc content the same grounded way, teach each concept with a small agent
> team, and meter usage against a plan.

1. `POST /v1/notebooks/{id}/sources/import` → `SourceConnectorEngine.import_source`: validate the
   `connector_type`, normalize the supplied text/transcript/exported content (stripping HTML when
   needed), then ingest via `RagEngine` — producing a real `source` + guide + a `source_import`
   provenance record. `GET /v1/notebooks/{id}/imports` lists them. The core never fetches remote
   URLs itself; a connector worker supplies the extracted text.
2. `POST /v1/notebooks/{id}/agent-teaching/start` → `TeachingEngine.start_multi_agent_session`:
   builds the cited concept progression, then three `AgentTurn`s per concept (explainer / verifier /
   coach). `GET /v1/agent-teaching/{id}` + `…/next` / `…/prev` navigate.
3. `GET /v1/billing/plans` lists Free/Scholar/Pro; `POST /v1/billing/{user}/subscribe` runs the
   `BillingProvider` (mock auto‑activates; Stripe returns a Checkout URL) and persists the
   subscription; metered actions call `PricingEngine.meter`, and `GET /v1/billing/usage/{user}`
   reports used/limit/remaining per action.

### G) "Sign in, scope data, watch the system" *(Phase 5)*
> 🟢 Create an account, get a token, and have requests run as you — with usage gated to your plan
> and the system's health visible.

1. `POST /v1/auth/register` / `POST /v1/auth/login` → `AuthEngine` hashes/verifies the password
   (PBKDF2) and returns a stateless **HS256 JWT**. The web client stores it and sends
   `Authorization: Bearer <token>` on every call.
2. When `STUDYLAB_REQUIRE_AUTH` is set, the gateway verifies the token on every non‑public route
   (else 401) and resolves the user; `authorize_notebook` enforces per‑user ownership.
3. When `STUDYLAB_ENFORCE_QUOTAS` is set, metered actions go through `PricingEngine.enforce`, which
   raises `QuotaExceededError` → HTTP **402** once the plan quota is spent.
4. `GET /metrics` returns the live observability snapshot (`MetricsCollector`): ask/refusal,
   citation coverage, verified rate, cache hit, and solve‑latency percentiles.

---

## 5. Technology choices

| Layer | Choice | Notes |
|---|---|---|
| Web | Next.js 15, React 19, TypeScript | Interactive client panels; `next build` (compile + typecheck + prerender) verified. |
| Services | Python 3.11+, stdlib `http.server` | Zero‑dependency HTTP via a shared mini‑router ([service_http.py](../packages/studylab_core/studylab_core/service_http.py)). |
| Persistence (local) | In‑memory or **SQLite** (stdlib) | Selected by `STUDYLAB_SQLITE_PATH`. |
| Persistence (target) | **Postgres** | Schema in [packages/db/migrations](../packages/db/migrations). |
| Vector search (target) | **Qdrant** | Adapter present; local hybrid used by default. |
| Cache (target) | **Redis** | In compose; app cache is currently in the store. |
| Voice (target) | **Gemini** | `GeminiVoiceProvider` when `GEMINI_API_KEY` set; mock otherwise. |
| Billing (target) | **Stripe** | `StripeBillingProvider` when `STRIPE_API_KEY` set; mock auto‑activates otherwise. |
| Auth (Phase 5) | **PBKDF2 + HS256 JWT** (stdlib) | Enforced when `STUDYLAB_REQUIRE_AUTH=true`; secret from `STUDYLAB_JWT_SECRET` (fail‑fast on dev default). |
| Observability (Phase 5) | in‑process counters at `/metrics` | Export to Prometheus/OTel in production. |
| Hardening (Phase 6) | CORS, sliding-window rate limit, input caps, per‑user ownership | `STUDYLAB_CORS_ORIGINS` / `STUDYLAB_RATE_LIMIT` / `STUDYLAB_MAX_SOURCE_CHARS`; rag binds loopback. |
| Collaboration (Phase 7) | notebook sharing (viewer/editor) + roles (student/instructor/admin) | Share-aware `authorize_notebook`; admin via `STUDYLAB_ADMIN_EMAILS`. |
| Monorepo | pnpm workspaces + Turborepo | [pnpm-workspace.yaml](../pnpm-workspace.yaml), [turbo.json](../turbo.json). |
| CI | CircleCI | [.circleci/config.yml](../.circleci/config.yml). |

See [11-current-status.md](11-current-status.md) for which of these are live vs. env‑gated
adapters.
