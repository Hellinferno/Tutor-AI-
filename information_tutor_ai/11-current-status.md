# 11 — Current Status (honest scope) 🟢🔵

The truthful picture of what is **real and verified**, what is an **env‑gated adapter**, and what
is **not built yet**. Keep this document accurate as the source of truth on project state.

> 🟢 **Plain English:** software is built in stages. This page is the honest scoreboard: green =
> works today and is tested; yellow = the "plug" is built but the real external service isn't
> wired in yet; grey = planned for a future stage.

---

## ✅ Done, working, and tested (Phase 0 → Phase 10)

| Area | State |
|---|---|
| Monorepo (pnpm + turbo), CI (CircleCI) | ✅ |
| Local env + `.env.example` | ✅ |
| Docker Compose (postgres, redis, qdrant, gateway, rag, solver, shared volume) | ✅ |
| Dockerfiles for gateway, rag, solver | ✅ |
| DB migration (full Phase 1–9 schema) | ✅ written |
| **Phase 10 — Postgres store** (`PostgresStudyLabStore`; mirrors SQLite surface; psycopg lazy-imported; activated by `DATABASE_URL` / `STUDYLAB_POSTGRES_URL`) | ✅ |
| **Phase 10 — Real embedding providers** (`OpenAIEmbeddingProvider`, `HttpEmbeddingProvider`, `make_embedding_provider` factory with safe fallback to local-hash) | ✅ |
| **Phase 10 — Live Qdrant client** (`QdrantHybridSearchAdapter.search_vector_ids`; activated by `QDRANT_URL`; rerank stays local + deterministic) | ✅ |
| **Phase 10 — Storage diagnostics** (`GET /v1/admin/storage` reports active store backend, Qdrant configured, embedding provider name; never leaks DSNs) | ✅ |
| Gateway + rag + solver services (runnable, `/health` + `/ready` + functional routes) | ✅ |
| Shared API contracts (OpenAPI + TypeScript types, Phase 0–7) | ✅ |
| Notebook creation, source upload, source guides | ✅ |
| Chunking with stable character offsets | ✅ |
| Hybrid retrieval (sparse + dense + rerank) | ✅ (local impl) |
| Strict citations + low‑confidence refusal | ✅ |
| Verified solver: symbolic, finance NPV, **real sandboxed code execution** | ✅ |
| Solution cache + step reveal | ✅ |
| 5 artifact types | ✅ |
| Notion export (real API + mock) | ✅ |
| **Durable SQLite persistence** (survives restart; all 4 phases) | ✅ |
| Prompt template library + loader | ✅ |
| Eval gate (15 cases, `false_verified_rate=0`) | ✅ |
| **Phase 2 — Teaching engine** (whiteboard concept progression, cited explanations) | ✅ |
| **Phase 2 — Quiz generation** (MCQ / true‑false / short‑answer; from notebook or topic) | ✅ |
| **Phase 2 — Question‑paper generation** (sectioned, marks, duration) | ✅ |
| **Phase 2 — Verified answer keys** (deterministic source/option checks) | ✅ |
| **Phase 2 — Auto‑eval + reports** (attempt scoring, weak/strong topics, summary) | ✅ |
| **Phase 3 — Spaced repetition** (SM‑2 revision cards, due queue, review/reschedule) | ✅ |
| **Phase 3 — Student model** (per‑topic mastery from eval reports, weak/strong topics) | ✅ |
| **Phase 3 — Progress analytics** (per‑attempt score trend, user summary) | ✅ |
| **Phase 3 — Voice I/O** (STT/TTS via env‑gated provider; mock default) | ✅ |
| **Phase 4 — Source connectors** (website / YouTube / audio / Google Doc / Slides → chunk + guide + cite) | ✅ |
| **Phase 4 — Multi‑agent teaching** (explainer + grounding‑verifier + practice‑coach turns per concept) | ✅ |
| **Phase 4 — Pricing & economics** (Free/Scholar/Pro plans, usage metering, quota checks, subscriptions) | ✅ |
| **Phase 5 — Authentication** (email/password, PBKDF2 hashing, stateless HS256 JWT) | ✅ |
| **Phase 5 — Authorization** (per‑user notebook ownership checks; env‑gated gateway bearer enforcement) | ✅ |
| **Phase 5 — Quota enforcement** (plan quotas hard‑gate metered actions → HTTP 402 when enabled) | ✅ |
| **Phase 5 — Observability** (`/metrics`: refusal rate, citation coverage, verified rate, cache hit, solve latency) | ✅ |
| **Phase 6 — Account self-service** (change/reset password, edit profile, delete account + cascade) | ✅ |
| **Phase 6 — Hardening** (CORS + preflight, rate limiting → 429, input-size caps, `/ready`, fail-fast JWT secret) | ✅ |
| **Phase 6 — Onboarding** (one-click "Load sample" notebook; account settings UI) | ✅ |
| **Phase 7 — Notebook sharing** (share with viewer/editor; "shared with me"; view‑vs‑edit access) | ✅ |
| **Phase 7 — Roles** (student / instructor / admin; admin‑only `/v1/admin/*`; `STUDYLAB_ADMIN_EMAILS`) | ✅ |
| **Phase 8 — Classrooms** (instructor‑owned classes, 6‑char join codes, enrollment, roster) | ✅ |
| **Phase 8 — Assignments** (instructor assigns quiz/paper to a class with optional due date) | ✅ |
| **Phase 8 — Submissions** (student submits → eval pipeline scores → submission linked to assignment) | ✅ |
| **Phase 8 — Class analytics** (per‑assignment completion rate + avg %; class overall avg; top weak topics) | ✅ |
| **Phase 8 — Admin role management** (`POST /v1/admin/users/{id}/role`; the way to mint instructors) | ✅ |
| **Phase 9 — Discussion comments** (threaded notebook comments; visible to owner + shared users) | ✅ |
| **Phase 9 — Submission feedback** (instructor feedback + optional grade override; final grade beats auto) | ✅ |
| **Phase 9 — Notifications** (inbox for share/enroll/assign/submit/grade/comment events; read + read-all) | ✅ |
| **Interactive web app** (Next 15) — all 20 panels wired to the gateway, responsive/mobile, no static mockups | ✅ |
| Test suite (211 tests) | ✅ |

**The Phase 1–10 acceptance gates pass.** See [10-testing-and-eval.md](10-testing-and-eval.md).

---

## 🟡 Built as adapters, not yet wired to live external services

These have working **contracts/seams** and a self‑contained default, but the production
integration needs an external service or credentials (and can't be runtime‑verified offline).

| Capability | What exists now | To go live |
|---|---|---|
| **Postgres persistence** | **Phase 10** — `PostgresStudyLabStore` built (mirrors the SQLite surface; psycopg lazy-imported; falls back to SQLite if the driver isn't installed) | Install `psycopg[binary]`, set `DATABASE_URL`, point at a running Postgres — `make_store_from_env` will pick it |
| **Qdrant vector search** | **Phase 10** — `QdrantHybridSearchAdapter.search_vector_ids` is a live HTTP client; retriever uses it as the candidate set, rerank stays local + deterministic | Point `QDRANT_URL` (+ optional `QDRANT_COLLECTION` / `QDRANT_API_KEY`) at a running Qdrant; payloads are indexed by `notebook_id` |
| **Real embeddings** | **Phase 10** — `OpenAIEmbeddingProvider` + `HttpEmbeddingProvider` + `make_embedding_provider` factory; local-hash is the safety fallback if a real provider errors | Set `OPENAI_API_KEY` (or `EMBEDDINGS_ENDPOINT` for any TEI-style server) and the factory picks it up; `/v1/admin/storage` confirms which one is live |
| **Real OCR** | OCR adapter seam (local placeholder) | Connect an OCR provider |
| **Redis cache** | Provisioned in compose; cache currently lives in the store | Move cache to Redis via `REDIS_URL` |
| **Voice STT/TTS** | `VoiceProvider` interface; `MockVoiceProvider` default, `GeminiVoiceProvider` real path | Set `GEMINI_API_KEY` to use the real provider |
| **Connector content fetching** | `SourceConnectorEngine` normalizes/validates extracted text, transcripts, and exports; chunk + guide + cite is the live path | Run a connector worker that fetches/transcribes/exports and posts the text (respecting robots/ToS) |
| **Billing / payments** | `BillingProvider` interface; `MockBillingProvider` default (auto‑activates), `StripeBillingProvider` real path (Checkout Session + webhook seam) | Set `STRIPE_API_KEY` and confirm activations from a webhook |
| **Auth enforcement** | First‑party email/password + JWT, per‑user authorization (IDOR‑safe), and rate limiting are fully built and tested; gateway bearer enforcement, hard quota gating, and rate limiting are **off by default** | Set `STUDYLAB_REQUIRE_AUTH=true` (+ a strong `STUDYLAB_JWT_SECRET`), `STUDYLAB_ENFORCE_QUOTAS=true`, `STUDYLAB_RATE_LIMIT=…` |
| **Metrics backend** | In‑process counters at `/metrics` (deterministic, dependency‑free) | Export to Prometheus / OpenTelemetry in production |
| **Password‑reset email** | Reset tokens are generated + verified; returned in the response only in mock mode (auth off / `STUDYLAB_AUTH_MOCK_EMAIL`) | Wire an email provider to deliver the token; production never returns it in the body |

> 🟢 **Why leave these as adapters?** It keeps the project **runnable and testable by anyone with
> no accounts or API keys**, while making the production swap a small, well‑defined change rather
> than a rewrite. Plans, quotas, usage metering, **auth, and observability are fully real and tested
> locally**; the env flags simply turn enforcement on, and only the *charge-the-card* step is gated
> behind `STRIPE_API_KEY`.

---

## ⚪ Not built yet (beyond the planned phases)

The specs ([Instructions/10-development-phases.md](../Instructions/10-development-phases.md)) define
Phases 0–4; **Phases 5–10 were added on top** to ship to real users: Phase 5 (auth, authorization,
quota enforcement, observability), Phase 6 (production hardening + user readiness: CORS, rate
limiting, input caps, account self‑service, onboarding), Phase 7 (collaboration — notebook
sharing with viewer/editor roles, "shared with me", and student/instructor/admin roles),
Phase 8 (classrooms — instructor‑owned classes, 6‑char join codes, assignments with due dates,
submission tracking, and per‑class analytics; plus admin role management to mint instructors),
Phase 9 (the social layer — threaded discussion comments on notebooks, instructor feedback
with optional grade override on submissions, and a notifications inbox emitted from every
multi‑user event), and Phase 10 (production persistence — a real Postgres store, a live Qdrant
client, OpenAI/HTTP embedding providers, and an admin storage‑diagnostics endpoint, all env‑gated
with a clean local fallback). What still remains as a later concern:

- **Native mobile apps** (iOS/Android) — the web app is fully **responsive** (works on phones), but
  there is no native shell yet.
- **Horizontal scaling / multi‑region** — the adapter seams (Postgres, Redis, Qdrant) are the
  intended scaling path; load‑balancing and autoscaling configs are not included.
- **OAuth / SSO** — first‑party email/password auth (with self‑service + reset) is built; social
  login is not.
- **Email delivery** — password‑reset tokens are generated/verified, but wiring an email provider
  to deliver them is a deployment step.

> 🟢 **Note on deterministic generation:** the teaching explanations, multi‑agent turns,
> quiz/paper questions, answer keys, revision cards, and mastery scores are built
> **deterministically from your uploaded sources, source guides, and your own attempt history** —
> not by a language model that might hallucinate. This keeps the product runnable offline and
> consistent with Phase 1's "no unverified claims" rule. Swapping in an LLM for richer phrasing
> (and real voice/billing providers via env keys) is an env‑gated enhancement.

---

## One‑line summary

> **Phase 0 → Phase 10 are complete, tested (211 tests), and self‑contained, and the web app is
> fully wired to the gateway (20 responsive panels, no static mockups).** Phase 5 added first‑party
> auth (PBKDF2 + JWT), per‑user authorization, env‑gated quota enforcement, and a `/metrics`
> endpoint; Phase 6 added production hardening (CORS, rate limiting, input‑size caps, `/ready`,
> IDOR‑safe ownership checks, fail‑fast JWT secret) and user readiness (account self‑service +
> sample onboarding); Phase 7 added collaboration — notebook **sharing** (viewer/editor) with a
> "shared with me" view, share‑aware authorization, and **roles** (student/instructor/admin) with
> admin‑only routes; Phase 8 added classrooms — instructor‑owned classes with short join codes,
> roster, assignments (quiz/paper with due dates), submission tracking through the eval pipeline,
> per‑class analytics (completion rate, average score, top weak topics), and an admin
> `POST /admin/users/{id}/role` route to mint instructors; Phase 9 added the social layer —
> threaded **discussion comments** on notebooks (owner + shared users can read/post), **instructor
> feedback** on submissions with an optional grade override (the final score listed and rolled into
> analytics beats the auto score), and a **notifications inbox** fed by every multi‑user event
> (share, enroll, assign, submit, grade, comment); **Phase 10 added production persistence** — a
> `PostgresStudyLabStore` mirroring the SQLite surface (psycopg lazy-imported), `OpenAIEmbedding
> Provider` + `HttpEmbeddingProvider` + a fallback‑safe `make_embedding_provider` factory, a live
> `QdrantHybridSearchAdapter.search_vector_ids` HTTP client that the retriever uses as the
> candidate set (rerank stays local + deterministic), and an admin `GET /v1/admin/storage`
> diagnostic that reports the active mix without leaking DSNs. OCR, Redis, the real voice provider,
> connector fetch‑workers, Stripe billing, a production metrics backend, and reset‑email delivery
> are intentionally left as env‑gated adapters; auth / quota / rate‑limit *enforcement* is built
> but off by default. Native mobile, horizontal‑scaling infra, and OAuth/SSO remain later concerns.
