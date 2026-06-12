from __future__ import annotations

from typing import Any

from .analytics import AnalyticsEngine
from .artifacts import ArtifactGenerator
from .eval import EvalEngine
from .models import ArtifactType, AttemptSourceType, Session
from .notion import NotionExporter
from .ocr import extract_text_from_image_payload
from .paper import PaperEngine
from .quiz import QuizEngine
from .rag import RagEngine
from .revision import RepetitionEngine
from .solver import SolverEngine
from .store import InMemoryStudyLabStore
from .student import StudentModel
from .teaching import TeachingEngine
from .voice import VoiceProvider, make_voice_provider


class StudyLabAPI:
    def __init__(self, store: InMemoryStudyLabStore | None = None, voice: VoiceProvider | None = None) -> None:
        self.store = store or InMemoryStudyLabStore()
        self.rag = RagEngine(self.store)
        self.solver = SolverEngine(self.store, self.rag)
        self.artifacts = ArtifactGenerator(self.store, self.rag)
        self.teaching = TeachingEngine(self.store, self.rag)
        self.quiz = QuizEngine(self.store, self.rag)
        self.paper = PaperEngine(self.store, self.rag, self.quiz)
        self.eval = EvalEngine(self.store)
        # Phase 3 engines
        self.revision = RepetitionEngine(self.store)
        self.student = StudentModel(self.store)
        self.analytics = AnalyticsEngine(self.store)
        self.voice = voice or make_voice_provider()

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

    # ── Phase 2: Teaching ─────────────────────────────────────────────────

    def start_teaching(self, notebook_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.start_session(notebook_id))

    def get_teaching_session(self, session_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.get_session(session_id))

    def teaching_next(self, session_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.next_concept(session_id))

    def teaching_prev(self, session_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.prev_concept(session_id))

    # ── Phase 2: Quizzes ──────────────────────────────────────────────────

    def generate_quiz(
        self,
        notebook_id: str,
        num_questions: int = 5,
        question_types: list[str] | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        return self.store.to_plain(self.quiz.generate_quiz(
            notebook_id=notebook_id,
            num_questions=num_questions,
            question_types=question_types,
            topic=topic,
        ))

    def get_quiz(self, quiz_id: str, include_answers: bool = False) -> dict[str, Any]:
        return self.store.to_plain(self.quiz.get_quiz(quiz_id, include_answers=include_answers))

    def get_quiz_answer_key(self, quiz_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.quiz.generate_answer_key(quiz_id))

    # ── Phase 2: Question Papers ──────────────────────────────────────────

    def generate_paper(
        self,
        notebook_id: str,
        sections: list[dict] | None = None,
        duration_minutes: int = 60,
        topic: str | None = None,
    ) -> dict[str, Any]:
        return self.store.to_plain(self.paper.generate_paper(
            notebook_id=notebook_id,
            sections=sections,
            duration_minutes=duration_minutes,
            topic=topic,
        ))

    def get_paper(self, paper_id: str, include_answers: bool = False) -> dict[str, Any]:
        return self.store.to_plain(self.paper.get_paper(paper_id, include_answers=include_answers))

    def get_paper_answer_key(self, paper_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.paper.generate_answer_key(paper_id))

    # ── Phase 2: Eval ─────────────────────────────────────────────────────

    def submit_attempt(
        self,
        source_id: str,
        source_type: AttemptSourceType,
        answers: list[dict],
        user_id: str = "demo-user",
    ) -> dict[str, Any]:
        attempt = self.eval.evaluate_attempt(
            source_id=source_id,
            source_type=source_type,
            user_answers=answers,
            user_id=user_id,
        )
        # Phase 3: auto-generate revision cards for weak topics
        self._auto_revision_from_weak_topics(attempt.id, user_id)
        return self.store.to_plain(attempt)

    def get_report(self, attempt_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.eval.generate_report(attempt_id))

    def _auto_revision_from_weak_topics(self, attempt_id: str, user_id: str) -> None:
        """Generate revision cards for weak topics after evaluation."""
        try:
            report = self.eval.generate_report(attempt_id)
            if report.weak_topics:
                attempt = self.store.require_attempt(attempt_id)
                # Find notebook_id from the quiz or paper source
                notebook_id = None
                if attempt.source_type == "quiz":
                    quiz = self.store.quizzes.get(attempt.source_id)
                    if quiz:
                        notebook_id = quiz.notebook_id if hasattr(quiz, 'notebook_id') else None
                elif attempt.source_type == "paper":
                    paper = self.store.question_papers.get(attempt.source_id)
                    if paper:
                        notebook_id = paper.notebook_id if hasattr(paper, 'notebook_id') else None
                if notebook_id:
                    self.revision.generate_cards(
                        notebook_id=notebook_id,
                        user_id=user_id,
                        topics=report.weak_topics,
                        source="eval_weak_topic",
                    )
        except Exception:
            pass  # Auto-generation is best-effort; don't fail the attempt submission

    # ── Phase 3: Revision Cards ───────────────────────────────────────────────

    def generate_revision_cards(
        self,
        notebook_id: str,
        topics: list[str] | None = None,
        user_id: str = "demo-user",
        source: str = "manual",
    ) -> dict[str, Any]:
        cards = self.revision.generate_cards(notebook_id=notebook_id, user_id=user_id, topics=topics, source=source)
        return {"cards": self.store.to_plain(cards)}

    def get_due_cards(self, user_id: str = "demo-user") -> dict[str, Any]:
        cards = self.revision.due_cards(user_id=user_id)
        return {"cards": self.store.to_plain(cards)}

    def review_card(self, card_id: str, correct: bool) -> dict[str, Any]:
        return self.store.to_plain(self.revision.review_card(card_id=card_id, correct=correct))

    def revision_stats(self, user_id: str = "demo-user") -> dict[str, Any]:
        return self.revision.card_stats(user_id=user_id)

    # ── Phase 3: Student Mastery ──────────────────────────────────────────────

    def compute_mastery(self, user_id: str, notebook_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.student.compute_mastery(user_id=user_id, notebook_id=notebook_id))

    def get_mastery(self, user_id: str, notebook_id: str) -> dict[str, Any]:
        state = self.student.get_knowledge_state(user_id=user_id, notebook_id=notebook_id)
        return self.store.to_plain(state) if state else {"user_id": user_id, "notebook_id": notebook_id, "masteries": [], "overall_score": 0.0, "weak_topics": [], "strong_topics": []}

    def get_weak_topics(self, user_id: str, notebook_id: str) -> dict[str, Any]:
        topics = self.student.weak_topics(user_id=user_id, notebook_id=notebook_id)
        return {"weak_topics": topics}

    # ── Phase 3: Sessions ─────────────────────────────────────────────────────

    def create_session(self, user_id: str, notebook_id: str, kind: str = "study") -> dict[str, Any]:
        self.store.require_notebook(notebook_id)
        session = Session(
            id=self.store.next_id("session"),
            user_id=user_id,
            notebook_id=notebook_id,
            kind=kind,
        )
        return self.store.to_plain(self.store.add_session(session))

    def end_session(self, session_id: str) -> dict[str, Any]:
        session = self.store.require_session(session_id)
        from datetime import datetime, timezone
        session.ended_at = datetime.now(timezone.utc).isoformat()
        if hasattr(self.store, 'save_session'):
            return self.store.to_plain(self.store.save_session(session))
        return self.store.to_plain(self.store.add_session(session))

    # ── Phase 3: Analytics ────────────────────────────────────────────────────

    def notebook_trends(self, notebook_id: str) -> dict[str, Any]:
        return {"trends": self.analytics.notebook_trends(notebook_id=notebook_id)}

    def user_summary(self, user_id: str = "demo-user") -> dict[str, Any]:
        return self.analytics.user_summary(user_id=user_id)

    # ── Phase 3: Voice ────────────────────────────────────────────────────────

    def speech_to_text(self, audio_base64: str, format: str = "wav") -> dict[str, Any]:
        return self.store.to_plain(self.voice.stt(audio_base64=audio_base64, format=format))

    def text_to_speech(self, text: str, format: str = "wav") -> dict[str, Any]:
        return self.store.to_plain(self.voice.tts(text=text, format=format))
