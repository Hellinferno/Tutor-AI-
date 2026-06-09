from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from .models import Citation, SourceChunk
from .store import InMemoryStudyLabStore
from .text_processing import make_citation, normalize_whitespace, tokenize


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        """Return a dense vector for text."""


class LocalHashEmbeddingProvider:
    """Deterministic dependency-free embedding stand-in.

    Production should replace this with OpenAI, Voyage, local bge/e5, or another
    embedding provider while preserving the retrieval contract.
    """

    def __init__(self, dimensions: int = 96) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


@dataclass
class RetrievalCandidate:
    chunk: SourceChunk
    sparse_score: float
    dense_score: float
    rerank_score: float

    @property
    def final_score(self) -> float:
        return round((self.sparse_score * 0.35) + (self.dense_score * 0.25) + (self.rerank_score * 0.40), 4)


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def sparse_score(query_tokens: list[str], chunk_tokens: list[str], document_frequency: Counter[str], document_count: int) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    chunk_counts = Counter(chunk_tokens)
    unique_query = set(query_tokens)
    score = 0.0
    for token in unique_query:
        tf = chunk_counts[token]
        if not tf:
            continue
        idf = math.log((document_count + 1) / (document_frequency[token] + 0.5)) + 1
        score += (1 + math.log(tf)) * idf
    coverage = len(unique_query.intersection(chunk_counts)) / max(1, len(unique_query))
    normalized = score / max(1.0, math.sqrt(len(chunk_tokens)))
    return min(1.0, (coverage * 0.65) + (normalized * 0.12))


def rerank_score(query: str, chunk: SourceChunk, sparse: float, dense: float) -> float:
    query_tokens = tokenize(query)
    chunk_text = chunk.text.lower()
    chunk_tokens = tokenize(chunk.text)
    if not query_tokens or not chunk_tokens:
        return 0.0

    phrase_bonus = 0.0
    normalized_query = normalize_whitespace(query.lower())
    if len(normalized_query) > 8 and normalized_query in normalize_whitespace(chunk_text):
        phrase_bonus = 0.2

    ordered_hits = 0
    cursor = 0
    for token in query_tokens:
        try:
            found = chunk_tokens.index(token, cursor)
        except ValueError:
            continue
        ordered_hits += 1
        cursor = found + 1
    proximity = ordered_hits / max(1, len(set(query_tokens)))

    numeric_or_formula_bonus = 0.0
    formula_terms = {"npv", "irr", "theta", "gradient", "mse", "regression", "cash", "flow"}
    if set(query_tokens).intersection(formula_terms) and set(query_tokens).intersection(chunk_tokens):
        numeric_or_formula_bonus = 0.15

    return min(1.0, (sparse * 0.45) + (dense * 0.25) + (proximity * 0.25) + phrase_bonus + numeric_or_formula_bonus)


class HybridRetriever:
    """Local implementation of the intended Qdrant hybrid retrieval pipeline."""

    def __init__(self, store: InMemoryStudyLabStore, embeddings: EmbeddingProvider | None = None) -> None:
        self.store = store
        self.embeddings = embeddings or LocalHashEmbeddingProvider()

    def retrieve(
        self,
        notebook_id: str,
        query: str,
        top_k: int = 4,
        candidate_k: int = 40,
        min_score: float = 0.16,
    ) -> list[Citation]:
        chunks = self.store.notebook_chunks(notebook_id)
        if not chunks:
            return []

        query_tokens = tokenize(query)
        document_frequency = Counter()
        tokenized_chunks = {}
        for chunk in chunks:
            tokens = tokenize(chunk.text)
            tokenized_chunks[chunk.id] = tokens
            document_frequency.update(set(tokens))

        query_vector = self.embeddings.embed(query)
        candidates = []
        for chunk in chunks:
            tokens = tokenized_chunks[chunk.id]
            sparse = sparse_score(query_tokens, tokens, document_frequency, len(chunks))
            dense = max(0.0, cosine(query_vector, self.embeddings.embed(chunk.text)))
            if sparse == 0.0 and dense < 0.08:
                continue
            rerank = rerank_score(query, chunk, sparse=sparse, dense=dense)
            candidates.append(RetrievalCandidate(chunk=chunk, sparse_score=sparse, dense_score=dense, rerank_score=rerank))

        candidates.sort(key=lambda item: item.final_score, reverse=True)
        selected = [candidate for candidate in candidates[:candidate_k] if candidate.final_score >= min_score]
        return [make_citation(self.store, candidate.chunk, candidate.final_score) for candidate in selected[:top_k]]


class QdrantHybridSearchAdapter:
    """Payload builder for the production Qdrant implementation.

    This keeps Phase 1 explicit about the intended storage/retrieval contract
    without making local tests depend on Qdrant or a network service.
    """

    collection_name = "source_chunks"

    def point_payload(self, chunk: SourceChunk, source_title: str) -> dict:
        return {
            "id": chunk.vector_id,
            "payload": {
                "notebook_id": chunk.notebook_id,
                "source_id": chunk.source_id,
                "source_title": source_title,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "text": chunk.text,
            },
        }

    def query_plan(self, notebook_id: str, query: str, top_k: int = 8) -> dict:
        return {
            "collection": self.collection_name,
            "filter": {"must": [{"key": "notebook_id", "match": {"value": notebook_id}}]},
            "prefetch": [
                {"using": "dense", "query": {"text": query}, "limit": 40},
                {"using": "sparse", "query": {"text": query}, "limit": 40},
            ],
            "rerank": {"using": "late_interaction", "query": {"text": query}, "limit": top_k},
        }
