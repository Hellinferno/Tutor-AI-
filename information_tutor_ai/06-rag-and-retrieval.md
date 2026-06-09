# 06 — RAG & Retrieval 🟢🔵

How Tutor‑AI answers questions **using only your sources**, with citations, and refuses when it
shouldn't guess.

---

## 🟢 The plain‑English version

"RAG" stands for **Retrieval‑Augmented Generation**. Instead of answering from memory, the app:

1. **Retrieves** the most relevant passages from *your* uploaded notes.
2. **Generates** an answer grounded in those passages, citing each one.

Two design promises make it trustworthy:

- **Every claim is cited** — you can see the exact source and location.
- **It refuses when support is weak** — better to say "not enough in your notes" than to invent.

---

## 🔵 The pipeline (current implementation)

Code: [retrieval.py](../packages/studylab_core/studylab_core/retrieval.py),
[rag.py](../packages/studylab_core/studylab_core/rag.py),
[text_processing.py](../packages/studylab_core/studylab_core/text_processing.py).

### Step 1 — Ingestion (when you upload a source)
- `chunk_text` splits the source into ~900‑char chunks with ~120‑char overlap, preferring
  sentence/paragraph boundaries, and records **exact `start_char`/`end_char` offsets** for each
  chunk (so citations are precise and stable).
- `make_source_guide` produces the summary, key concepts (top tokens), and suggested questions.

### Step 2 — Hybrid retrieval (when you ask)
For each chunk, three signals are computed and blended:

| Signal | What it captures | Roughly |
|---|---|---|
| **Sparse** | exact keyword / term overlap (TF‑IDF‑like, with query coverage) | good for formulas, tickers, function names, definitions |
| **Dense** | semantic similarity via an embedding vector (cosine) | good for paraphrases / meaning |
| **Rerank** | phrase match + in‑order proximity + a small formula‑term bonus | sharpens the top results |

Final score (in code): `0.35·sparse + 0.25·dense + 0.40·rerank`. Chunks are sorted, filtered by
`min_score` (default `0.16`), and the top `k` (default `4`) become **citations** carrying
`source_title`, `chunk_index`, `start_char`, `end_char`, `snippet`, and `score`.

### Step 3 — Grounded answer or refusal
`RagEngine.ask`:
- **No chunks clear the bar →** returns `grounding = "insufficient_source_support"`, empty
  citations, and helpful next steps. (This is the tested **refusal** behaviour.)
- **Otherwise →** selects the most query‑relevant sentences from the cited chunks and returns an
  answer with inline `[source_title, chunk N]` citations and suggested follow‑ups.

---

## The embedding provider (and why it's swappable)

Retrieval depends on an `EmbeddingProvider` interface. The default is
`LocalHashEmbeddingProvider` — a **deterministic, dependency‑free stand‑in** so the whole pipeline
runs and is testable with no API keys or model downloads.

> 🟢 **Plain English:** an "embedding" turns text into a list of numbers that captures meaning, so
> the computer can measure how similar two pieces of text are. We ship a simple local version so
> everything works offline; a production‑grade model (OpenAI, Voyage, local bge/e5, …) can be
> dropped in behind the same interface without changing the rest of the code.

---

## The production target: Qdrant

`QdrantHybridSearchAdapter` builds the exact **point payload** and **query plan** for a real
Qdrant vector database:

- Collection `source_chunks`; named vectors `dense`, `sparse`, optional `late_interaction`.
- Payload: `notebook_id`, `source_id`, `source_title`, `chunk_index`, `start_char`, `end_char`,
  `text`.
- Query: filter by notebook → prefetch dense + sparse candidates → rerank to the final set.

This keeps the storage/retrieval contract explicit while local tests stay free of any network
dependency. **Status:** the adapter describes the contract; the live wiring to a running Qdrant is
an env‑gated next step (see [11-current-status.md](11-current-status.md)).
