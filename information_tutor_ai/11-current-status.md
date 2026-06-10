# 11 — Current Status (honest scope) 🟢🔵

The truthful picture of what is **real and verified**, what is an **env‑gated adapter**, and what
is **not built yet**. Keep this document accurate as the source of truth on project state.

> 🟢 **Plain English:** software is built in stages. This page is the honest scoreboard: green =
> works today and is tested; yellow = the "plug" is built but the real external service isn't
> wired in yet; grey = planned for a future stage.

---

## ✅ Done, working, and tested (Phase 0 + Phase 1 + Phase 2)

| Area | State |
|---|---|
| Monorepo (pnpm + turbo), CI (CircleCI) | ✅ |
| Local env + `.env.example` | ✅ |
| Docker Compose (postgres, redis, qdrant, gateway, rag, solver, shared volume) | ✅ |
| Dockerfiles for gateway, rag, solver | ✅ |
| DB migration (full Phase 1 + Phase 2 schema) | ✅ written |
| Gateway + rag + solver services (runnable, `/health` + functional routes) | ✅ |
| Shared API contracts (OpenAPI + TypeScript types) | ✅ |
| Notebook creation, source upload, source guides | ✅ |
| Chunking with stable character offsets | ✅ |
| Hybrid retrieval (sparse + dense + rerank) | ✅ (local impl) |
| Strict citations + low‑confidence refusal | ✅ |
| Verified solver: symbolic, finance NPV, **real sandboxed code execution** | ✅ |
| Solution cache + step reveal | ✅ |
| 5 artifact types | ✅ |
| Notion export (real API + mock) | ✅ |
| **Durable SQLite persistence** (survives restart) | ✅ |
| Prompt template library + loader | ✅ |
| Eval gate (15 cases, `false_verified_rate=0`) | ✅ |
| Web app build (Next 15) | ✅ |
| **Phase 2 — Teaching engine** (whiteboard concept progression, cited explanations) | ✅ |
| **Phase 2 — Quiz generation** (MCQ / true‑false / short‑answer; from notebook or topic) | ✅ |
| **Phase 2 — Question‑paper generation** (sectioned, marks, duration) | ✅ |
| **Phase 2 — Verified answer keys** (deterministic source/option checks) | ✅ |
| **Phase 2 — Auto‑eval + reports** (attempt scoring, weak/strong topics, summary) | ✅ |
| Test suite (44 tests) | ✅ |

**The Phase 1 and Phase 2 acceptance gates pass.** See [10-testing-and-eval.md](10-testing-and-eval.md).

---

## 🟡 Built as adapters, not yet wired to live external services

These have working **contracts/seams** and a self‑contained default, but the production
integration needs an external service or credentials (and can't be runtime‑verified offline).

| Capability | What exists now | To go live |
|---|---|---|
| **Postgres persistence** | Full SQL migration; SQLite store mirrors the contract | Add a Postgres-backed store using `DATABASE_URL` |
| **Qdrant vector search** | `QdrantHybridSearchAdapter` (payload + query plan); local hybrid retriever is the live path | Connect a running Qdrant via `QDRANT_URL` |
| **Real embeddings** | `EmbeddingProvider` interface; `LocalHashEmbeddingProvider` default | Plug in OpenAI / Voyage / local bge‑e5 |
| **Real OCR** | OCR adapter seam (local placeholder) | Connect an OCR provider |
| **Redis cache** | Provisioned in compose; cache currently lives in the store | Move cache to Redis via `REDIS_URL` |

> 🟢 **Why leave these as adapters?** It keeps the project **runnable and testable by anyone with
> no accounts or API keys**, while making the production swap a small, well‑defined change rather
> than a rewrite.

---

## ⚪ Not built yet (later phases)

From [Instructions/10-development-phases.md](../Instructions/10-development-phases.md):

- **Phase 3** — student model, spaced‑repetition scheduling, progress analytics, voice I/O,
  weak‑topic revision cards.
- **Phase 4** — multi‑agent teaching, mobile, scaling/pricing/economics, more source connectors
  (websites, YouTube, audio, Google Docs/Slides).

*(The `sessions` and `revision_cards` tables already exist in the schema in anticipation of
Phase 3.)*

> 🟢 **Note on Phase 2 quality:** the teaching explanations, quiz questions, and paper questions are
> built **deterministically from your uploaded sources** (and source guides), with answer keys
> verified by structural checks — not by a language model that might hallucinate. This keeps Phase 2
> runnable offline and consistent with Phase 1's "no unverified claims" rule. Swapping in an LLM
> for richer phrasing is a later, env‑gated enhancement.

---

## One‑line summary

> **Phase 0 + Phase 1 + Phase 2 are complete, tested (44 tests), and self‑contained.** Postgres,
> Qdrant, real embeddings/OCR, and Redis are intentionally left as env‑gated adapters; Phases 3–4
> are planned and not yet built.
