# 12 — Glossary 🟢

Plain‑English definitions of the terms used across this project and these docs. Skim as needed.

| Term | Meaning |
|---|---|
| **Notebook** | A labelled container for your study material and questions (e.g. "ML 101"). |
| **Source** | A piece of material you upload into a notebook (notes, PDF text, slides). |
| **Source guide** | An auto‑generated summary + key concepts + suggested questions for one source. |
| **Chunk** | A small slice of a source. Long text is split into chunks so the app can find and cite the exact relevant part. |
| **Offset (start_char/end_char)** | The exact character positions a chunk occupies in its source — lets a citation point to a precise span. |
| **Citation** | A reference showing *where* an answer came from: source title, chunk, position, snippet, and a relevance score. |
| **Grounding** | Whether an answer is backed by your sources (`from_sources`) or refused for lack of support (`insufficient_source_support`). |
| **RAG (Retrieval‑Augmented Generation)** | Answering by first *retrieving* relevant passages, then *generating* an answer grounded in them — instead of answering from memory. |
| **Retrieval** | The act of finding the most relevant chunks for a question. |
| **Sparse score** | A keyword‑overlap measure — good at exact terms, formulas, names. |
| **Dense score** | A meaning‑similarity measure using "embeddings" — good at paraphrases. |
| **Embedding** | A list of numbers representing a piece of text's meaning, so similarity can be measured mathematically. |
| **Rerank** | A second‑pass scoring that sharpens the top results (phrase match, word order, formula bonus). |
| **Hybrid retrieval** | Combining sparse + dense + rerank into one ranking. |
| **min_score / top_k** | Thresholds: ignore chunks below `min_score`; keep the best `top_k`. |
| **Solver** | The component that computes answers to math/finance/code questions. |
| **Verified / verify_method** | Whether an answer was confirmed by an objective checker, and which one (`symbolic`, `formula`, `code_exec`) — or `unverified`. |
| **False‑verified rate** | How often the app *wrongly* claims an answer is verified. Project target: **zero**. |
| **Symbolic** | Solving by evaluating a math expression directly (e.g. `2+2*3`). |
| **NPV (Net Present Value)** | A finance formula that discounts future cash flows to today's value. |
| **Sandbox** | A locked‑down, disconnected mini‑environment where user code runs safely (no internet, files, or secrets; time‑limited). |
| **AST (Abstract Syntax Tree)** | The parsed structure of code; used to inspect and allow/deny a snippet *before* running it. |
| **Allowlist** | The explicit list of things permitted (e.g. safe modules); everything else is denied. |
| **OCR (Optical Character Recognition)** | Turning an image of text into actual text. |
| **Artifact** | A generated study document: summary notes, study guide, planner, timetable, or revision cards. |
| **Revision cards / spaced repetition** | Flashcard‑style prompts reviewed on a widening schedule to aid memory. |
| **SM‑2** | The classic spaced‑repetition algorithm: each correct review grows the interval (and an "easiness factor"); a miss resets it. |
| **Student model / mastery** | A per‑topic score (0–1) of how well you know each topic, derived from your quiz/paper results; splits topics into weak vs. strong. |
| **Analytics** | Progress views built from your attempt history: a per‑attempt score trend and an overall summary. |
| **STT / TTS** | Speech‑to‑Text (transcribe audio) and Text‑to‑Speech (read text aloud); via an env‑gated voice provider (mock by default). |
| **Notion export** | Sending a generated artifact into the Notion note‑taking app. |
| **Gateway** | The backend "front door" service that receives requests from the website. |
| **Service** | A standalone backend program (here: gateway, rag, solver). |
| **Store** | The component that saves/loads data (in‑memory, SQLite, or Postgres). |
| **In‑memory** | Data kept only in RAM — fast but lost on restart. |
| **SQLite** | A self‑contained database stored in a single file — durable, no server needed. |
| **Postgres** | A full production database server (the long‑term target). |
| **Qdrant** | A specialised "vector database" for fast semantic search (production target). |
| **Redis** | An in‑memory data store often used for caching (provisioned for later use). |
| **Embedding provider** | A pluggable component that produces embeddings; swappable without changing other code. |
| **Monorepo** | One repository holding multiple apps/packages together. |
| **pnpm / Turborepo** | Tools that manage and build a JavaScript monorepo. |
| **CI (Continuous Integration)** | Automated checks that run on every code push (here, CircleCI). |
| **Eval / benchmark** | A fixed set of test problems used to measure solver quality. |
| **Env‑gated adapter** | Code whose live behaviour turns on only when an environment variable / external service is configured. |
| **Phase 0–3 / Phase 4** | Built stages: foundation (0), grounded RAG + verified solver (1), teaching/quiz/paper (2), memory/revision/analytics/voice (3). Phase 4 (multi‑agent, mobile, more connectors) is planned. |
