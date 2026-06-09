from __future__ import annotations

from .models import Artifact, ArtifactType, Citation
from .rag import RagEngine
from .store import InMemoryStudyLabStore


class ArtifactGenerator:
    def __init__(self, store: InMemoryStudyLabStore, rag: RagEngine) -> None:
        self.store = store
        self.rag = rag

    def generate(self, notebook_id: str, artifact_type: ArtifactType, title: str | None = None) -> Artifact:
        notebook = self.store.require_notebook(notebook_id)
        guides = self.store.notebook_guides(notebook_id)
        citations = self._notebook_citations(notebook_id)
        concepts = []
        for guide in guides:
            concepts.extend(guide.key_concepts)
        concepts = list(dict.fromkeys(concepts))[:10] or ["core concepts"]

        artifact_title = title or self._default_title(notebook.title, artifact_type)
        content = self._render(artifact_type=artifact_type, notebook_title=notebook.title, concepts=concepts, guides=guides)
        artifact = Artifact(
            id=self.store.next_id("artifact"),
            notebook_id=notebook_id,
            artifact_type=artifact_type,
            title=artifact_title,
            content_markdown=content,
            citations=citations,
        )
        return self.store.add_artifact(artifact)

    def _notebook_citations(self, notebook_id: str) -> list[Citation]:
        chunks = self.store.notebook_chunks(notebook_id)[:4]
        citations = []
        for chunk in chunks:
            source = self.store.require_source(chunk.source_id)
            citations.append(
                Citation(
                    source_id=source.id,
                    source_title=source.title,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    snippet=chunk.text[:240].strip(),
                    score=1.0,
                )
            )
        return citations

    def _default_title(self, notebook_title: str, artifact_type: ArtifactType) -> str:
        labels = {
            "summary_notes": "Summary Notes",
            "study_guide": "Study Guide",
            "planner": "Study Planner",
            "timetable": "Timetable",
            "revision_cards": "Revision Cards",
        }
        return f"{notebook_title} - {labels[artifact_type]}"

    def _render(self, artifact_type: ArtifactType, notebook_title: str, concepts: list[str], guides: list) -> str:
        if artifact_type == "summary_notes":
            lines = [f"# Summary Notes for {notebook_title}", "", "## Key Ideas"]
            lines.extend(f"- {concept}" for concept in concepts)
            lines.append("")
            lines.append("## Source Summaries")
            lines.extend(f"- {guide.summary}" for guide in guides)
            return "\n".join(lines)
        if artifact_type == "study_guide":
            lines = [f"# Study Guide for {notebook_title}", "", "## Concepts to Master"]
            lines.extend(f"- {concept}" for concept in concepts)
            lines.append("")
            lines.append("## Practice Prompts")
            lines.extend(f"- Explain {concept} with one formula or example." for concept in concepts[:6])
            return "\n".join(lines)
        if artifact_type == "planner":
            lines = [f"# Study Planner for {notebook_title}", "", "## This Week"]
            for index, concept in enumerate(concepts[:5], start=1):
                lines.append(f"- Day {index}: Read source notes on {concept}, then solve 3 checkable questions.")
            return "\n".join(lines)
        if artifact_type == "timetable":
            lines = [f"# Timetable for {notebook_title}", "", "| Day | Focus | Output |", "|---|---|---|"]
            for index, concept in enumerate(concepts[:5], start=1):
                lines.append(f"| Day {index} | {concept} | Summary notes + one verified solve |")
            return "\n".join(lines)
        if artifact_type == "revision_cards":
            lines = [f"# Revision Cards for {notebook_title}", ""]
            for concept in concepts[:8]:
                lines.append(f"## {concept}")
                lines.append("- Prompt: Define it, give an example, and solve one related problem.")
                lines.append("- Schedule: Day 1, Day 3, Day 7, Day 15, Day 30")
                lines.append("")
            return "\n".join(lines)
        raise ValueError(f"Unsupported artifact type: {artifact_type}")
