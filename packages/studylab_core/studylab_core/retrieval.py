from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from .models import Citation, SourceChunk
from .store import InMemoryStudyLabStore
from .text_processing import make_citation, normalize_whitespace, tokenize


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, text: str) -> list[float]:
        """Return a dense vector for text."""


class LocalHashEmbeddingProvider:
    """Deterministic dependency-free embedding stand-in.

    Production replaces this with OpenAI, Voyage, local bge/e5, or any HTTP-served
    embedding endpoint while preserving the retrieval contract. See
    ``make_embedding_provider`` for how the active provider is picked from the env.
    """

    name = "local_hash"

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


def _normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class HttpEmbeddingProvider:
    """POSTs ``{"input": "<text>"}`` to ``EMBEDDINGS_ENDPOINT`` and reads ``embedding``.

    Endpoint shape is intentionally generic so the same provider works against a
    local bge/e5 server, a TEI deployment, or a small wrapper around an inference
    pod — anything that returns JSON ``{"embedding": [floats]}``. Set ``EMBEDDINGS_API_KEY``
    to add a ``Bearer`` header. The response is unit-normalized so downstream cosine
    scoring is consistent across providers.
    """

    name = "http"

    def __init__(self, endpoint: str | None = None, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.endpoint = endpoint or os.getenv("EMBEDDINGS_ENDPOINT") or ""
        if not self.endpoint:
            raise RuntimeError("EMBEDDINGS_ENDPOINT not set")
        self.api_key = api_key or os.getenv("EMBEDDINGS_API_KEY")
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"input": text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - configured endpoint
            payload = json.loads(resp.read().decode("utf-8"))
        vector = payload.get("embedding")
        if not isinstance(vector, list):
            raise RuntimeError(f"embeddings endpoint returned no `embedding`: {payload!r}")
        return _normalize_vector([float(v) for v in vector])


class OpenAIEmbeddingProvider:
    """Calls the OpenAI ``/v1/embeddings`` REST endpoint directly via stdlib HTTP.

    Avoids pulling in the ``openai`` SDK so installation stays dependency-light.
    Model defaults to ``OPENAI_EMBEDDING_MODEL`` (or ``text-embedding-3-small``);
    base URL is ``OPENAI_BASE_URL`` so an Azure / proxy deployment also works.
    """

    name = "openai"
    _DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None, timeout: float = 30.0) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL") or self._DEFAULT_MODEL
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"model": self.model, "input": text}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(f"{self.base_url}/v1/embeddings", data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - configured endpoint
            payload = json.loads(resp.read().decode("utf-8"))
        data = payload.get("data") or []
        if not data or "embedding" not in data[0]:
            raise RuntimeError(f"OpenAI embeddings returned no data: {payload!r}")
        return _normalize_vector([float(v) for v in data[0]["embedding"]])


def make_embedding_provider() -> EmbeddingProvider:
    """Pick the embedding provider from the environment.

    Priority: explicit ``EMBEDDINGS_PROVIDER`` switch ->
    ``OPENAI_API_KEY`` (OpenAI) -> ``EMBEDDINGS_ENDPOINT`` (HTTP) -> local hash fallback.
    If a real provider is configured but fails to initialize, the local fallback is
    used so the request path never collapses entirely.
    """

    explicit = (os.getenv("EMBEDDINGS_PROVIDER") or "").strip().lower()
    if explicit in {"local", "local_hash", "none"}:
        return LocalHashEmbeddingProvider()
    try:
        if explicit == "openai" or (not explicit and os.getenv("OPENAI_API_KEY")):
            return OpenAIEmbeddingProvider()
    except Exception:
        pass
    try:
        if explicit == "http" or (not explicit and os.getenv("EMBEDDINGS_ENDPOINT")):
            return HttpEmbeddingProvider()
    except Exception:
        pass
    return LocalHashEmbeddingProvider()


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
    """Local implementation of the intended Qdrant hybrid retrieval pipeline.

    When ``qdrant`` is supplied (auto-selected from env via ``QDRANT_URL``) the
    retriever first asks Qdrant for the candidate set of `vector_id`s for the
    notebook, then runs the local rerank against those chunks. This keeps the
    rerank deterministic + side-effect-free while letting Qdrant be the source
    of truth for dense + sparse recall in production.
    """

    def __init__(
        self,
        store: InMemoryStudyLabStore,
        embeddings: EmbeddingProvider | None = None,
        qdrant: "QdrantHybridSearchAdapter | None" = None,
    ) -> None:
        self.store = store
        self.embeddings = embeddings or LocalHashEmbeddingProvider()
        self.qdrant = qdrant

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
        if self.qdrant is not None and self.qdrant.is_live():
            # Ask Qdrant for the recall set; if it answers, restrict reranking to those
            # chunks. If Qdrant is unreachable or returns nothing, fall back to the full
            # notebook so we never silently drop to empty results.
            try:
                qdrant_ids = self.qdrant.search_vector_ids(
                    notebook_id=notebook_id,
                    query=query,
                    query_vector=self.embeddings.embed(query),
                    limit=candidate_k,
                )
                if qdrant_ids:
                    matching = [c for c in chunks if c.vector_id in qdrant_ids]
                    if matching:
                        chunks = matching
            except Exception:
                pass

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
    """Payload builder + live client for Qdrant hybrid search.

    The class doubles as the Phase 1 contract (``point_payload`` / ``query_plan``)
    and the **Phase 10 live client** — when constructed with a ``url``, ``search_vector_ids``
    actually POSTs to ``{url}/collections/{collection}/points/search`` and returns the
    matching `vector_id`s for the notebook. ``is_live()`` tells the retriever whether
    to consult Qdrant vs. fall back to local-only recall.
    """

    collection_name = "source_chunks"

    def __init__(
        self,
        url: str | None = None,
        collection: str | None = None,
        api_key: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.url = (url or os.getenv("QDRANT_URL") or "").rstrip("/")
        self.collection = collection or os.getenv("QDRANT_COLLECTION") or self.collection_name
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.timeout = timeout

    def is_live(self) -> bool:
        return bool(self.url)

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
            "collection": self.collection,
            "filter": {"must": [{"key": "notebook_id", "match": {"value": notebook_id}}]},
            "prefetch": [
                {"using": "dense", "query": {"text": query}, "limit": 40},
                {"using": "sparse", "query": {"text": query}, "limit": 40},
            ],
            "rerank": {"using": "late_interaction", "query": {"text": query}, "limit": top_k},
        }

    def search_vector_ids(
        self,
        notebook_id: str,
        query: str,
        query_vector: list[float],
        limit: int = 40,
    ) -> list[str]:
        """POST a notebook-scoped search to Qdrant and return matching vector_ids.

        Uses Qdrant's classic ``points/search`` API since it's available on every
        Qdrant version and doesn't require the newer prefetch+rerank pipeline.
        ``query`` is accepted for parity with the engine contract but the live
        call uses the dense vector to keep the request shape predictable.
        """
        if not self.is_live():
            return []
        body = json.dumps({
            "vector": query_vector,
            "filter": {
                "must": [{"key": "notebook_id", "match": {"value": notebook_id}}],
            },
            "limit": int(limit),
            "with_payload": False,
            "with_vector": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        req = urllib.request.Request(
            f"{self.url}/collections/{self.collection}/points/search",
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - configured endpoint
            payload = json.loads(resp.read().decode("utf-8"))
        return [str(hit["id"]) for hit in (payload.get("result") or []) if hit.get("id") is not None]


def make_qdrant_adapter() -> QdrantHybridSearchAdapter | None:
    """Pick a Qdrant adapter from the environment. Returns None when not configured."""

    if not os.getenv("QDRANT_URL"):
        return None
    return QdrantHybridSearchAdapter()
