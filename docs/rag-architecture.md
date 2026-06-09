# Phase 1 RAG Architecture

StudyLab should use a NotebookLM-style source-first RAG system, with hybrid retrieval and reranking as the default.

## Pipeline

```text
source upload
-> extract text
-> chunk with stable offsets
-> source guide
-> dense + sparse indexing
-> notebook-filtered hybrid retrieval
-> rerank
-> cited evidence set
-> answer or insufficient-source-support response
```

## Production Store

- Postgres stores notebooks, sources, chunks, source guides, artifacts, and citation metadata.
- Qdrant stores `source_chunks` vectors.
- Qdrant payloads must include `notebook_id`, `source_id`, `source_title`, `chunk_index`, `start_char`, `end_char`, and `text`.

## Retrieval Policy

- Use sparse retrieval for exact formulas, finance terms, code identifiers, definitions, and syllabus terms.
- Use dense retrieval for conceptual phrasing and paraphrase matching.
- Rerank the combined candidate set before answering.
- Return no grounded answer when final evidence scores are below threshold.
- Every grounded answer must include citations tied to exact chunks and snippets.
