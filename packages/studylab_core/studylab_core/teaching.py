from __future__ import annotations

from .models import AgentTurn, MultiAgentTeachingSession, WhiteboardConcept, WhiteboardSession
from .rag import RagEngine
from .store import InMemoryStudyLabStore
from .text_processing import make_citation


class TeachingEngine:
    def __init__(self, store: InMemoryStudyLabStore, rag: RagEngine) -> None:
        self.store = store
        self.rag = rag

    def _build_concepts(self, notebook_id: str) -> list[WhiteboardConcept]:
        """Build the cited concept progression for a notebook (no persistence).

        Shared by the single-track whiteboard and the multi-agent session so the
        two teaching modes stay consistent and neither creates a stray session.
        """
        notebook = self.store.require_notebook(notebook_id)
        guides = self.store.notebook_guides(notebook_id)
        chunks = self.store.notebook_chunks(notebook_id)

        concepts: list[WhiteboardConcept] = []
        seen: set[str] = set()
        for guide in guides:
            for concept_name in guide.key_concepts:
                if concept_name in seen:
                    continue
                seen.add(concept_name)
                explanation, citations = self._build_concept_explanation(concept_name, chunks)
                concepts.append(WhiteboardConcept(
                    name=concept_name,
                    explanation=explanation,
                    citations=citations,
                    whiteboard=self._build_whiteboard(concept_name),
                ))

        if not concepts:
            concepts.append(WhiteboardConcept(
                name=notebook.title,
                explanation="No structured concepts were extracted from this notebook's sources. Try uploading more detailed material.",
                citations=[],
                whiteboard=[{"type": "diagram", "text": "Upload sources -> extract concepts -> teach with citations"}],
            ))
        return concepts

    def start_session(self, notebook_id: str) -> WhiteboardSession:
        session = WhiteboardSession(
            id=self.store.next_id("session"),
            notebook_id=notebook_id,
            current_concept_idx=0,
            concepts=self._build_concepts(notebook_id),
        )
        return self.store.add_whiteboard_session(session)

    def get_session(self, session_id: str) -> WhiteboardSession:
        return self.store.require_whiteboard_session(session_id)

    def next_concept(self, session_id: str) -> WhiteboardSession:
        session = self.store.require_whiteboard_session(session_id)
        if session.current_concept_idx < len(session.concepts) - 1:
            session.current_concept_idx += 1
        else:
            session.completed = True
        if hasattr(self.store, "save_whiteboard_session"):
            self.store.save_whiteboard_session(session)
        return session

    def prev_concept(self, session_id: str) -> WhiteboardSession:
        session = self.store.require_whiteboard_session(session_id)
        if session.current_concept_idx > 0:
            session.current_concept_idx -= 1
            session.completed = False
        if hasattr(self.store, "save_whiteboard_session"):
            self.store.save_whiteboard_session(session)
        return session

    def start_multi_agent_session(self, notebook_id: str) -> MultiAgentTeachingSession:
        concepts = self._build_concepts(notebook_id)
        turns: list[AgentTurn] = []
        for index, concept in enumerate(concepts):
            turns.extend(self._agent_turns_for_concept(index, concept))
        session = MultiAgentTeachingSession(
            id=self.store.next_id("agent_session"),
            notebook_id=notebook_id,
            current_concept_idx=0,
            concepts=concepts,
            agent_turns=turns,
        )
        return self.store.add_multi_agent_teaching_session(session)

    def get_multi_agent_session(self, session_id: str) -> MultiAgentTeachingSession:
        return self.store.require_multi_agent_teaching_session(session_id)

    def multi_agent_next(self, session_id: str) -> MultiAgentTeachingSession:
        session = self.store.require_multi_agent_teaching_session(session_id)
        if session.current_concept_idx < len(session.concepts) - 1:
            session.current_concept_idx += 1
        else:
            session.completed = True
        if hasattr(self.store, "save_multi_agent_teaching_session"):
            self.store.save_multi_agent_teaching_session(session)
        return session

    def multi_agent_prev(self, session_id: str) -> MultiAgentTeachingSession:
        session = self.store.require_multi_agent_teaching_session(session_id)
        if session.current_concept_idx > 0:
            session.current_concept_idx -= 1
            session.completed = False
        if hasattr(self.store, "save_multi_agent_teaching_session"):
            self.store.save_multi_agent_teaching_session(session)
        return session

    def _build_concept_explanation(self, concept: str, chunks) -> tuple[str, list]:
        matching = [c for c in chunks if concept.lower() in c.text.lower()]
        if matching:
            source_texts = [c.text[:300].strip() for c in matching[:2]]
            citations = [make_citation(self.store, chunk, 1.0) for chunk in matching[:2]]
            return f"From your sources: {' '.join(source_texts)}", citations
        return f"{concept} is a key topic in this notebook. Review your source material for detailed explanations and examples.", []

    def _build_whiteboard(self, concept: str) -> list[dict]:
        lowered = concept.lower()
        elements = [{"type": "diagram", "text": f"{concept} -> definition -> example -> checked practice"}]
        if "gradient" in lowered or "theta" in lowered:
            elements.append({"type": "math", "katex": "\\theta := \\theta - \\eta \\nabla J(\\theta)"})
            elements.append({"type": "code", "lang": "python", "text": "theta = theta - learning_rate * gradient"})
        if "npv" in lowered or "cash" in lowered or "finance" in lowered:
            elements.append({"type": "math", "katex": "NPV = \\sum_{t=0}^{n} \\frac{C_t}{(1+r)^t}"})
        return elements

    def _agent_turns_for_concept(self, concept_index: int, concept: WhiteboardConcept) -> list[AgentTurn]:
        citation_count = len(concept.citations)
        grounding = "source-grounded" if citation_count else "needs more source support"
        confidence = 0.92 if citation_count else 0.55
        return [
            AgentTurn(
                agent_id="explainer",
                role="concept_explainer",
                concept_index=concept_index,
                title=f"Explain {concept.name}",
                content=concept.explanation,
                citations=concept.citations,
                confidence=confidence,
            ),
            AgentTurn(
                agent_id="verifier",
                role="grounding_verifier",
                concept_index=concept_index,
                title="Grounding check",
                content=f"This teaching step is {grounding} with {citation_count} cited passage(s).",
                citations=concept.citations,
                confidence=1.0 if citation_count else 0.5,
            ),
            AgentTurn(
                agent_id="coach",
                role="practice_coach",
                concept_index=concept_index,
                title="Practice move",
                content=f"Ask the learner to restate {concept.name}, then solve one checked practice item before moving on.",
                citations=concept.citations[:1],
                confidence=0.86,
            ),
        ]
