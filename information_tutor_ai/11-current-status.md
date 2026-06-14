# 11 — Current Status (honest scope) 🟢🔵

The truthful picture of what is **real and verified**, what is an **env‑gated adapter**, and what
is **not built yet**. Keep this document accurate as the source of truth on project state.

> 🟢 **Plain English:** software is built in stages. This page is the honest scoreboard: green =
> works today and is tested; yellow = the "plug" is built but the real external service isn't
> wired in yet; grey = planned for a future stage.

---

## ✅ Done, working, and tested (Phase 0 + Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5)

| Area | State |
|---|---|
| Monorepo (pnpm + turbo), CI (CircleCI) | ✅ |
| Local env + `.env.example` | ✅ |
| Docker Compose (postgres, redis, qdrant, gateway, rag, solver, shared volume) | ✅ |
| Dockerfiles for gateway, rag, solver | ✅ |
| DB migration (full Phase 1 + 2 + 3 + 4 + 5 schema) | ✅ written |
| Gateway + rag + solver services (runnable, `/health` + functional routes) | ✅ |
| Shared API contracts (OpenAPI + TypeScript types, Phase 0–5) | ✅ |
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
| **Interactive web app** (Next 15) — all 16 panels wired to the gateway, responsive/mobile, no static mockups | ✅ |
| Test suite (111 tests) | ✅ |

**The Phase 1, 2, 3, 4, and 5 acceptance gates pass.** See [10-testing-and-eval.md](10-testing-and-eval.md).

---

## 🟡 Built as adapters, not yet wired to live external services

These have working **contracts/seams** and a self‑contained default, but the production
integration needs an external service or credentials (and can't be runtime‑verified offline).

| Capability | What exists now | To go live |
|---|---|---|
| **Postgres persistence** | Full SQL migration (Phase 1–5); SQLite store mirrors the contract | Add a Postgres-backed store using `DATABASE_URL` |
| **Qdrant vector search** | `QdrantHybridSearchAdapter` (payload + query plan); local hybrid retriever is the live path | Connect a running Qdrant via `QDRANT_URL` |
| **Real embeddings** | `EmbeddingProvider` interface; `LocalHashEmbeddingProvider` default | Plug in OpenAI / Voyage / local bge‑e5 |
| **Real OCR** | OCR adapter seam (local placeholder) | Connect an OCR provider |
| **Redis cache** | Provisioned in compose; cache currently lives in the store | Move cache to Redis via `REDIS_URL` |
| **Voice STT/TTS** | `VoiceProvider` interface; `MockVoiceProvider` default, `GeminiVoiceProvider` real path | Set `GEMINI_API_KEY` to use the real provider |
| **Connector content fetching** | `SourceConnectorEngine` normalizes/validates extracted text, transcripts, and exports; chunk + guide + cite is the live path | Run a connector worker that fetches/transcribes/exports and posts the text (respecting robots/ToS) |
| **Billing / payments** | `BillingProvider` interface; `MockBillingProvider` default (auto‑activates), `StripeBillingProvider` real path (Checkout Session + webhook seam) | Set `STRIPE_API_KEY` and confirm activations from a webhook |
| **Auth enforcement** | First‑party email/password + JWT are fully built and tested; gateway bearer enforcement and hard quota gating are **off by default** | Set `STUDYLAB_REQUIRE_AUTH=true` (+ a strong `STUDYLAB_JWT_SECRET`) and `STUDYLAB_ENFORCE_QUOTAS=true` |
| **Metrics backend** | In‑process counters at `/metrics` (deterministic, dependency‑free) | Export to Prometheus / OpenTelemetry in production |

> 🟢 **Why leave these as adapters?** It keeps the project **runnable and testable by anyone with
> no accounts or API keys**, while making the production swap a small, well‑defined change rather
> than a rewrite. Plans, quotas, usage metering, **auth, and observability are fully real and tested
> locally**; the env flags simply turn enforcement on, and only the *charge-the-card* step is gated
> behind `STRIPE_API_KEY`.

---

## ⚪ Not built yet (beyond the planned phases)

The specs ([Instructions/10-development-phases.md](../Instructions/10-development-phases.md)) define
Phases 0–4; **Phase 5 ("production readiness": auth, authorization, quota enforcement, observability)
was added on top** to address the one remaining unbuilt item from
[Instructions/09-engineering-scope-definition.md](../Instructions/09-engineering-scope-definition.md)
("Full production auth"). What still remains as a later concern:

- **Native mobile apps** (iOS/Android) — the web app is fully **responsive** (works on phones), but
  there is no native shell yet.
- **Horizontal scaling / multi‑region** — the adapter seams (Postgres, Redis, Qdrant) are the
  intended scaling path; load‑balancing and autoscaling configs are not included.
- **OAuth / SSO and password reset** — first‑party email/password auth is built; social login and
  reset‑email flows are not.

> 🟢 **Note on deterministic generation:** the teaching explanations, multi‑agent turns,
> quiz/paper questions, answer keys, revision cards, and mastery scores are built
> **deterministically from your uploaded sources, source guides, and your own attempt history** —
> not by a language model that might hallucinate. This keeps the product runnable offline and
> consistent with Phase 1's "no unverified claims" rule. Swapping in an LLM for richer phrasing
> (and real voice/billing providers via env keys) is an env‑gated enhancement.

---

## One‑line summary

> **Phase 0 → Phase 5 are complete, tested (111 tests), and self‑contained, and the web app is fully
> wired to the gateway (16 responsive panels, no static mockups).** Phase 5 adds first‑party
> auth (PBKDF2 + JWT), per‑user authorization, env‑gated quota enforcement, and a `/metrics`
> observability endpoint. Postgres, Qdrant, real embeddings/OCR, Redis, the real voice provider,
> connector fetch‑workers, Stripe billing, and a production metrics backend are intentionally left as
> env‑gated adapters; auth/quota *enforcement* is built but off by default. Native mobile,
> horizontal‑scaling infra, and OAuth/SSO remain later concerns.
