# 04 - System Architecture

## High-level
```text
Web app
  -> Gateway
      -> RAG service
      -> Solver service
      -> Artifact service
      -> Notion export adapter
      -> Media/OCR service

Postgres: notebooks, sources, chunks, guides, questions, solutions, artifacts
Qdrant: dense/sparse vectors for source_chunks
Redis: solution cache and session scratch
Sandbox: isolated code execution
Frontier API: hard or non-verifiable tail only
```

## RAG architecture
StudyLab uses a NotebookLM-inspired source-first RAG pipeline:

1. Upload source into a notebook.
2. Extract text.
3. Chunk with stable character offsets.
4. Generate source guide.
5. Index chunks in Postgres and Qdrant.
6. Retrieve with hybrid search: dense semantic + sparse keyword/formula.
7. Rerank candidate chunks.
8. Answer only from evidence or return insufficient-source-support.
9. Attach strict citations.

## Qdrant collection
- Collection: `source_chunks`
- Dense vector: semantic embedding.
- Sparse vector: keyword/formula/BM25-style representation.
- Optional late-interaction vector for reranking.
- Payload: `notebook_id`, `source_id`, `source_title`, `chunk_index`, `start_char`, `end_char`, `text`.

## Solver pipeline
```text
question
-> normalize + hash
-> Redis cache lookup
-> optional notebook retrieval
-> solve
-> objective verification
-> persist solution and steps
-> return verified/unverified answer
```

## Verification matrix
- Code: isolated sandbox execution.
- Math/stats: symbolic or numeric checks.
- Finance: formula evaluation.
- Conceptual/open-ended: cited but unverified unless cross-check passes.

## Notion export
Generated artifacts are rendered as Notion-compatible blocks and exported to a private page by default. Parent page or database support is optional configuration.

## Current implementation status
The repo includes a local dependency-free version of the RAG and solver core. Qdrant, Redis, Postgres, and Notion are represented by contracts/adapters so the product can be tested before full infrastructure is connected.
