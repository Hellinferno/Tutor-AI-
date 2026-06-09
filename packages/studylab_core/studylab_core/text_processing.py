from __future__ import annotations

import math
import re
from collections import Counter

from .models import Citation, SourceChunk, SourceGuide
from .store import InMemoryStudyLabStore


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "why",
    "with",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]*|\d+(?:\.\d+)?", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[tuple[str, int, int]]:
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[tuple[str, int, int]] = []
    start = 0
    while start < len(cleaned):
        hard_end = min(start + chunk_size, len(cleaned))
        end = hard_end
        if hard_end < len(cleaned):
            boundary = max(cleaned.rfind("\n\n", start, hard_end), cleaned.rfind(". ", start, hard_end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            real_start = start + (len(cleaned[start:end]) - len(cleaned[start:end].lstrip()))
            chunks.append((chunk, real_start, end))
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def make_source_guide(text: str, source_id: str) -> SourceGuide:
    sentences = [normalize_whitespace(sentence) for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]
    summary = " ".join(sentences[:3])[:800] or "No summary available for this source yet."
    token_counts = Counter(tokenize(text))
    key_concepts = [token for token, _count in token_counts.most_common(8)]
    if not key_concepts:
        key_concepts = ["source overview"]
    suggested_questions = [
        f"What are the main ideas about {key_concepts[0]}?",
        f"Explain {key_concepts[min(1, len(key_concepts) - 1)]} using this source.",
        "Which formulas, steps, or definitions should I memorize?",
    ]
    return SourceGuide(
        source_id=source_id,
        summary=summary,
        key_concepts=key_concepts,
        suggested_questions=suggested_questions,
    )


def score_chunk(query_tokens: list[str], chunk: SourceChunk) -> float:
    chunk_tokens = tokenize(chunk.text)
    if not query_tokens or not chunk_tokens:
        return 0.0
    query_counts = Counter(query_tokens)
    chunk_counts = Counter(chunk_tokens)
    overlap = sum(min(count, chunk_counts[token]) for token, count in query_counts.items())
    coverage = overlap / max(1, len(set(query_tokens)))
    density = overlap / math.sqrt(len(chunk_tokens))
    return round(coverage * 0.75 + density * 0.25, 4)


def make_citation(store: InMemoryStudyLabStore, chunk: SourceChunk, score: float) -> Citation:
    source = store.require_source(chunk.source_id)
    snippet = normalize_whitespace(chunk.text[:360])
    return Citation(
        source_id=chunk.source_id,
        source_title=source.title,
        chunk_index=chunk.chunk_index,
        start_char=chunk.start_char,
        end_char=chunk.end_char,
        snippet=snippet,
        score=score,
    )


def select_relevant_sentences(query: str, chunks: list[SourceChunk], max_sentences: int = 4) -> list[str]:
    query_tokens = set(tokenize(query))
    selected: list[str] = []
    for chunk in chunks:
        for sentence in re.split(r"(?<=[.!?])\s+", chunk.text):
            sentence = normalize_whitespace(sentence)
            if not sentence:
                continue
            if query_tokens.intersection(tokenize(sentence)):
                selected.append(sentence)
            if len(selected) >= max_sentences:
                return selected
    return selected
