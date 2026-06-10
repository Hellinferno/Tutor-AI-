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
| **Web app** | [apps/web](../apps/web) | Next.js 15 / React 19 UI (notebook chat, solve, sources, artifacts, teaching, quiz, paper, report panels). |
| **Gateway service** | [services/gateway](../services/gateway) | HTTP front door exposing the full API (incl. Phase 2 teaching/quiz/paper/report routes). Uses the env‑selected store. |
| **RAG service** | [services/rag](../services/rag) | Standalone HTTP service for notebook/source/ask/artifact + Phase 2 teaching/quiz/paper/report routes. |
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

---

## 5. Technology choices

| Layer | Choice | Notes |
|---|---|---|
| Web | Next.js 15, React 19, TypeScript | Static‑prerendered build verified. |
| Services | Python 3.11+, stdlib `http.server` | Zero‑dependency HTTP via a shared mini‑router ([service_http.py](../packages/studylab_core/studylab_core/service_http.py)). |
| Persistence (local) | In‑memory or **SQLite** (stdlib) | Selected by `STUDYLAB_SQLITE_PATH`. |
| Persistence (target) | **Postgres** | Schema in [packages/db/migrations](../packages/db/migrations). |
| Vector search (target) | **Qdrant** | Adapter present; local hybrid used by default. |
| Cache (target) | **Redis** | In compose; app cache is currently in the store. |
| Monorepo | pnpm workspaces + Turborepo | [pnpm-workspace.yaml](../pnpm-workspace.yaml), [turbo.json](../turbo.json). |
| CI | CircleCI | [.circleci/config.yml](../.circleci/config.yml). |

See [11-current-status.md](11-current-status.md) for which of these are live vs. env‑gated
adapters.
