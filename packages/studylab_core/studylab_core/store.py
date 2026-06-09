from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import uuid4

from .models import Artifact, Notebook, Solution, Source, SourceChunk, SourceGuide


class InMemoryStudyLabStore:
    """Local development store used before Postgres, Redis, and Qdrant are connected."""

    def __init__(self) -> None:
        self.notebooks: dict[str, Notebook] = {}
        self.sources: dict[str, Source] = {}
        self.chunks: dict[str, SourceChunk] = {}
        self.guides: dict[str, SourceGuide] = {}
        self.solutions: dict[str, Solution] = {}
        self.solution_by_hash: dict[str, str] = {}
        self.artifacts: dict[str, Artifact] = {}

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    def add_notebook(self, title: str, user_id: str = "demo-user") -> Notebook:
        notebook = Notebook(id=self.next_id("notebook"), title=title, user_id=user_id)
        self.notebooks[notebook.id] = notebook
        return notebook

    def add_source(self, notebook_id: str, title: str, kind: str, text: str) -> Source:
        self.require_notebook(notebook_id)
        source = Source(
            id=self.next_id("source"),
            notebook_id=notebook_id,
            title=title,
            kind=kind,
            text=text,
        )
        self.sources[source.id] = source
        return source

    def add_chunk(
        self,
        source_id: str,
        notebook_id: str,
        chunk_index: int,
        text: str,
        start_char: int,
        end_char: int,
    ) -> SourceChunk:
        chunk = SourceChunk(
            id=self.next_id("chunk"),
            source_id=source_id,
            notebook_id=notebook_id,
            chunk_index=chunk_index,
            text=text,
            start_char=start_char,
            end_char=end_char,
            vector_id=f"local:{source_id}:{chunk_index}",
        )
        self.chunks[chunk.id] = chunk
        return chunk

    def set_guide(self, guide: SourceGuide) -> SourceGuide:
        self.guides[guide.source_id] = guide
        return guide

    def add_solution(self, solution: Solution) -> Solution:
        self.solutions[solution.id] = solution
        self.solution_by_hash[solution.question_hash] = solution.id
        return solution

    def save_solution(self, solution: Solution) -> Solution:
        self.solutions[solution.id] = solution
        return solution

    def add_artifact(self, artifact: Artifact) -> Artifact:
        self.artifacts[artifact.id] = artifact
        return artifact

    def get_cached_solution(self, question_hash: str) -> Solution | None:
        solution_id = self.solution_by_hash.get(question_hash)
        if not solution_id:
            return None
        return self.solutions[solution_id]

    def require_notebook(self, notebook_id: str) -> Notebook:
        try:
            return self.notebooks[notebook_id]
        except KeyError as exc:
            raise KeyError(f"Notebook not found: {notebook_id}") from exc

    def require_source(self, source_id: str) -> Source:
        try:
            return self.sources[source_id]
        except KeyError as exc:
            raise KeyError(f"Source not found: {source_id}") from exc

    def require_solution(self, solution_id: str) -> Solution:
        try:
            return self.solutions[solution_id]
        except KeyError as exc:
            raise KeyError(f"Solution not found: {solution_id}") from exc

    def notebook_chunks(self, notebook_id: str) -> list[SourceChunk]:
        self.require_notebook(notebook_id)
        chunks = [chunk for chunk in self.chunks.values() if chunk.notebook_id == notebook_id]
        return sorted(chunks, key=lambda chunk: (chunk.source_id, chunk.chunk_index))

    def notebook_guides(self, notebook_id: str) -> list[SourceGuide]:
        source_ids = {source.id for source in self.sources.values() if source.notebook_id == notebook_id}
        return [guide for source_id, guide in self.guides.items() if source_id in source_ids]

    def to_plain(self, value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, list):
            return [self.to_plain(item) for item in value]
        if isinstance(value, dict):
            return {key: self.to_plain(item) for key, item in value.items()}
        return value
