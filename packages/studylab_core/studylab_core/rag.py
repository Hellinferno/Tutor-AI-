from __future__ import annotations

from .models import AskResponse, Citation, Source, SourceGuide
from .retrieval import HybridRetriever
from .store import InMemoryStudyLabStore
from .text_processing import chunk_text, make_source_guide, select_relevant_sentences


class RagEngine:
    def __init__(self, store: InMemoryStudyLabStore) -> None:
        self.store = store
        self.retriever = HybridRetriever(store)

    def create_notebook(self, title: str, user_id: str = "demo-user"):
        return self.store.add_notebook(title=title, user_id=user_id)

    def ingest_source(self, notebook_id: str, title: str, text: str, kind: str = "notes") -> tuple[Source, SourceGuide]:
        if not text.strip():
            raise ValueError("Source text is empty")
        source = self.store.add_source(notebook_id=notebook_id, title=title, kind=kind, text=text)
        for index, (chunk, start_char, end_char) in enumerate(chunk_text(text)):
            self.store.add_chunk(
                source_id=source.id,
                notebook_id=notebook_id,
                chunk_index=index,
                text=chunk,
                start_char=start_char,
                end_char=end_char,
            )
        guide = self.store.set_guide(make_source_guide(text=text, source_id=source.id))
        return source, guide

    def retrieve(self, notebook_id: str, query: str, top_k: int = 4, min_score: float = 0.16) -> list[Citation]:
        return self.retriever.retrieve(notebook_id=notebook_id, query=query, top_k=top_k, min_score=min_score)

    def ask(self, notebook_id: str, query: str) -> AskResponse:
        citations = self.retrieve(notebook_id=notebook_id, query=query)
        if not citations:
            return AskResponse(
                answer=(
                    "I do not have enough support in your uploaded sources to answer this as a grounded response. "
                    "Try selecting a more relevant source, uploading more material, or asking for a general explanation."
                ),
                grounding="insufficient_source_support",
                citations=[],
                suggested_followups=["Upload a source about this topic", "Ask a narrower question"],
            )

        chunk_lookup = {(chunk.source_id, chunk.chunk_index): chunk for chunk in self.store.notebook_chunks(notebook_id)}
        chunks = [chunk_lookup[(citation.source_id, citation.chunk_index)] for citation in citations]
        sentences = select_relevant_sentences(query, chunks)
        if not sentences:
            sentences = [citation.snippet for citation in citations[:2]]
        answer_lines = ["From your sources:"]
        for index, sentence in enumerate(sentences[:4], start=1):
            citation = citations[min(index - 1, len(citations) - 1)]
            answer_lines.append(f"{index}. {sentence} [{citation.source_title}, chunk {citation.chunk_index}]")
        guides = self.store.notebook_guides(notebook_id)
        followups = []
        for guide in guides:
            followups.extend(guide.suggested_questions[:1])
        return AskResponse(
            answer="\n".join(answer_lines),
            grounding="from_sources",
            citations=citations,
            suggested_followups=followups[:3],
        )
