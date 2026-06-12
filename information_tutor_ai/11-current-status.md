# 11 — Current Status (honest scope) 🟢🔵

The truthful picture of what is **real and verified**, what is an **env‑gated adapter**, and what
is **not built yet**. Keep this document accurate as the source of truth on project state.

> 🟢 **Plain English:** software is built in stages. This page is the honest scoreboard: green =
> works today and is tested; yellow = the "plug" is built but the real external service isn't
> wired in yet; grey = planned for a future stage.

---

## ✅ Done, working, and tested (Phase 0 + Phase 1 + Phase 2 + Phase 3)

| Area | State |
|---|---|
| Monorepo (pnpm + turbo), CI (CircleCI) | ✅ |
| Local env + `.env.example` | ✅ |
| Docker Compose (postgres, redis, qdrant, gateway, rag, solver, shared volume) | ✅ |
| Dockerfiles for gateway, rag, solver | ✅ |
| DB migration (full Phase 1 + 2 + 3 schema) | ✅ written |
| Gateway + rag + solver services (runnable, `/health` + functional routes) | ✅ |
| Shared API contracts (OpenAPI Phase 0–3 + TypeScript types) | ✅ |
| Notebook creation, source upload, source guides | ✅ |
| Chunking with stable character offsets | ✅ |
| Hybrid retrieval (sparse + dense + rerank) | ✅ (local impl) |
| Strict citations + low‑confidence refusal | ✅ |
| Verified solver: symbolic, finance NPV, **real sandboxed code execution** | ✅ |
| Solution cache + step reveal | ✅ |
| 5 artifact types | ✅ |
| Notion export (real API + mock) | ✅ |
| **Durable SQLite persistence** (survives restart; all 3 phases) | ✅ |
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
| **Interactive web app** (Next 15) — all 10 panels wired to the gateway, no static mockups | ✅ |
| Test suite (64 tests) | ✅ |

**The Phase 1, 2, and 3 acceptance gates pass.** See [10-testing-and-eval.md](10-testing-and-eval.md).

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
| **Voice STT/TTS** | `VoiceProvider` interface; `MockVoiceProvider` default, `GeminiVoiceProvider` real path | Set `GEMINI_API_KEY` to use the real provider |

> 🟢 **Why leave these as adapters?** It keeps the project **runnable and testable by anyone with
> no accounts or API keys**, while making the production swap a small, well‑defined change rather
> than a rewrite.

---

## ⚪ Not built yet (later phases)

From [Instructions/10-development-phases.md](../Instructions/10-development-phases.md):

- **Phase 4** — multi‑agent teaching, mobile, scaling/pricing/economics, more source connectors
  (websites, YouTube, audio, Google Docs/Slides).

> 🟢 **Note on Phase 2–3 quality:** the teaching explanations, quiz/paper questions, answer keys,
> revision cards, and mastery scores are built **deterministically from your uploaded sources,
> source guides, and your own attempt history** — not by a language model that might hallucinate.
> This keeps the product runnable offline and consistent with Phase 1's "no unverified claims"
> rule. Swapping in an LLM for richer phrasing (and a real voice provider via `GEMINI_API_KEY`) is
> an env‑gated enhancement.

---

## One‑line summary

> **Phase 0 + Phase 1 + Phase 2 + Phase 3 are complete, tested (64 tests), and self‑contained, and
> the web app is fully wired to the gateway (no static mockups).** Postgres, Qdrant, real
> embeddings/OCR, Redis, and the real voice provider are intentionally left as env‑gated adapters;
> Phase 4 is planned and not yet built.
