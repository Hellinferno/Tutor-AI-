from __future__ import annotations

from typing import Any

from .artifacts import ArtifactGenerator
from .models import ArtifactType
from .notion import NotionExporter
from .ocr import extract_text_from_image_payload
from .rag import RagEngine
from .solver import SolverEngine
from .store import InMemoryStudyLabStore


class StudyLabAPI:
    def __init__(self, store: InMemoryStudyLabStore | None = None) -> None:
        self.store = store or InMemoryStudyLabStore()
        self.rag = RagEngine(self.store)
        self.solver = SolverEngine(self.store, self.rag)
        self.artifacts = ArtifactGenerator(self.store, self.rag)

    def create_notebook(self, title: str, user_id: str = "demo-user") -> dict[str, Any]:
        return self.store.to_plain(self.rag.create_notebook(title=title, user_id=user_id))

    def upload_source(self, notebook_id: str, title: str, text: str, kind: str = "notes") -> dict[str, Any]:
        source, guide = self.rag.ingest_source(notebook_id=notebook_id, title=title, text=text, kind=kind)
        return {"source": self.store.to_plain(source), "source_guide": self.store.to_plain(guide)}

    def get_source(self, source_id: str) -> dict[str, Any]:
        source = self.store.require_source(source_id)
        guide = self.store.guides.get(source_id)
        return {"source": self.store.to_plain(source), "source_guide": self.store.to_plain(guide)}

    def ask_notebook(self, notebook_id: str, query: str) -> dict[str, Any]:
        return self.store.to_plain(self.rag.ask(notebook_id=notebook_id, query=query))

    def solve(
        self,
        content: str,
        subject: str = "ai_ds",
        input_type: str = "text",
        notebook_id: str | None = None,
    ) -> dict[str, Any]:
        question = extract_text_from_image_payload(content) if input_type == "image" else content
        return self.store.to_plain(self.solver.solve(question=question, subject=subject, notebook_id=notebook_id))

    def reveal(self, solution_id: str, step_idx: int) -> dict[str, Any]:
        return self.solver.reveal_step(solution_id=solution_id, step_idx=step_idx)

    def generate_artifact(
        self,
        notebook_id: str,
        artifact_type: ArtifactType,
        title: str | None = None,
    ) -> dict[str, Any]:
        return self.store.to_plain(self.artifacts.generate(notebook_id=notebook_id, artifact_type=artifact_type, title=title))

    def export_to_notion(
        self,
        artifact_id: str,
        parent_page_id: str | None = None,
        data_source_id: str | None = None,
        mock: bool | None = None,
    ) -> dict[str, Any]:
        artifact = self.store.artifacts[artifact_id]
        result = NotionExporter(mock=mock).export_artifact(
            artifact=artifact,
            parent_page_id=parent_page_id,
            data_source_id=data_source_id,
        )
        return self.store.to_plain(result)
