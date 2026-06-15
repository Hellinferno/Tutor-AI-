from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import uuid4

from .models import (
    AnswerKey,
    Artifact,
    Attempt,
    EvalReport,
    Notebook,
    NotebookShare,
    QuestionPaper,
    Quiz,
    QuizQuestion,
    RevisionCard,
    Session,
    Solution,
    Source,
    SourceChunk,
    SourceGuide,
    SourceImport,
    StudentProfile,
    Subscription,
    TopicMastery,
    MultiAgentTeachingSession,
    UsageRecord,
    User,
    WhiteboardSession,
)


class InMemoryStudyLabStore:
    """Local development store used before Postgres, Redis, and Qdrant are connected."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.notebooks: dict[str, Notebook] = {}
        self.sources: dict[str, Source] = {}
        self.chunks: dict[str, SourceChunk] = {}
        self.guides: dict[str, SourceGuide] = {}
        self.solutions: dict[str, Solution] = {}
        self.solution_by_hash: dict[str, str] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.source_imports: dict[str, SourceImport] = {}

        # Phase 2 stores
        self.whiteboard_sessions: dict[str, WhiteboardSession] = {}
        self.multi_agent_teaching_sessions: dict[str, MultiAgentTeachingSession] = {}
        self.quizzes: dict[str, Quiz] = {}
        self.quiz_questions: dict[str, QuizQuestion] = {}
        self.question_papers: dict[str, QuestionPaper] = {}
        self.attempts: dict[str, Attempt] = {}
        self.answer_keys: dict[str, AnswerKey] = {}
        self.eval_reports: dict[str, EvalReport] = {}

        # Phase 3 stores
        self.revision_cards: dict[str, RevisionCard] = {}
        self.sessions: dict[str, Session] = {}
        self.student_profiles: dict[str, StudentProfile] = {}
        self.topic_masteries: dict[str, TopicMastery] = {}

        # Phase 4 stores (pricing & economics)
        self.subscriptions: dict[str, Subscription] = {}
        self.usage_records: dict[str, UsageRecord] = {}

        # Phase 7 stores (collaboration & sharing)
        self.notebook_shares: dict[str, NotebookShare] = {}

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    # ── Phase 5: Users & auth ────────────────────────────────────────────

    def add_user(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def save_user(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def require_user(self, user_id: str) -> User:
        try:
            return self.users[user_id]
        except KeyError as exc:
            raise KeyError(f"User not found: {user_id}") from exc

    def get_user_by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def all_users(self) -> list[User]:
        return sorted(self.users.values(), key=lambda u: u.created_at)

    # ── Phase 7: Notebook sharing ────────────────────────────────────────

    def add_share(self, share: NotebookShare) -> NotebookShare:
        self.notebook_shares[share.id] = share
        return share

    def remove_share(self, share_id: str) -> None:
        self.notebook_shares.pop(share_id, None)

    def shares_for_notebook(self, notebook_id: str) -> list[NotebookShare]:
        return [s for s in self.notebook_shares.values() if s.notebook_id == notebook_id]

    def shares_for_user(self, user_id: str) -> list[NotebookShare]:
        return [s for s in self.notebook_shares.values() if s.shared_with_id == user_id]

    def share_for(self, notebook_id: str, user_id: str) -> NotebookShare | None:
        for s in self.notebook_shares.values():
            if s.notebook_id == notebook_id and s.shared_with_id == user_id:
                return s
        return None

    def delete_user(self, user_id: str) -> None:
        """Delete a user and cascade-remove their owned data (account deletion)."""
        notebook_ids = {nb.id for nb in self.notebooks.values() if nb.user_id == user_id}
        source_ids = {s.id for s in self.sources.values() if s.notebook_id in notebook_ids}
        profile_ids = {p.id for p in self.student_profiles.values() if p.user_id == user_id}
        # Capture quiz/paper/attempt ids before dropping, so derived rows cascade too.
        graded_ids = {q.id for q in self.quizzes.values() if q.notebook_id in notebook_ids}
        graded_ids |= {p.id for p in self.question_papers.values() if p.notebook_id in notebook_ids}
        attempt_ids = {a.id for a in self.attempts.values() if a.user_id == user_id}

        def _drop(collection: dict, predicate) -> None:
            for key in [k for k, v in collection.items() if predicate(v)]:
                del collection[key]

        # Notebook-scoped data
        _drop(self.notebooks, lambda v: v.id in notebook_ids)
        _drop(self.sources, lambda v: v.notebook_id in notebook_ids)
        _drop(self.chunks, lambda v: v.notebook_id in notebook_ids)
        _drop(self.guides, lambda v: v.source_id in source_ids)
        _drop(self.artifacts, lambda v: v.notebook_id in notebook_ids)
        _drop(self.whiteboard_sessions, lambda v: v.notebook_id in notebook_ids)
        _drop(self.multi_agent_teaching_sessions, lambda v: v.notebook_id in notebook_ids)
        _drop(self.quizzes, lambda v: v.notebook_id in notebook_ids)
        _drop(self.question_papers, lambda v: v.notebook_id in notebook_ids)
        _drop(self.source_imports, lambda v: v.notebook_id in notebook_ids)
        # Derived grading data (keyed by quiz/paper or attempt)
        _drop(self.answer_keys, lambda v: v.source_id in graded_ids)
        _drop(self.eval_reports, lambda v: v.attempt_id in attempt_ids)
        # User-scoped data
        _drop(self.attempts, lambda v: v.user_id == user_id)
        _drop(self.revision_cards, lambda v: v.user_id == user_id)
        _drop(self.sessions, lambda v: v.user_id == user_id)
        _drop(self.student_profiles, lambda v: v.user_id == user_id)
        _drop(self.topic_masteries, lambda v: v.student_profile_id in profile_ids)
        _drop(self.subscriptions, lambda v: v.user_id == user_id)
        _drop(self.usage_records, lambda v: v.user_id == user_id)
        # Shares the user owns (notebooks deleted) or that were granted to them
        _drop(self.notebook_shares, lambda v: v.notebook_id in notebook_ids or v.shared_with_id == user_id or v.owner_id == user_id)
        self.users.pop(user_id, None)

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

    def add_source_import(self, source_import: SourceImport) -> SourceImport:
        self.source_imports[source_import.id] = source_import
        return source_import

    def require_source_import(self, import_id: str) -> SourceImport:
        try:
            return self.source_imports[import_id]
        except KeyError as exc:
            raise KeyError(f"Source import not found: {import_id}") from exc

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

    # ── Phase 2: Teaching, Quizzes, Papers, Eval ──────────────────────────

    def add_whiteboard_session(self, session: WhiteboardSession) -> WhiteboardSession:
        self.whiteboard_sessions[session.id] = session
        return session

    def add_multi_agent_teaching_session(self, session: MultiAgentTeachingSession) -> MultiAgentTeachingSession:
        self.multi_agent_teaching_sessions[session.id] = session
        return session

    def save_multi_agent_teaching_session(self, session: MultiAgentTeachingSession) -> MultiAgentTeachingSession:
        self.multi_agent_teaching_sessions[session.id] = session
        return session

    def require_multi_agent_teaching_session(self, session_id: str) -> MultiAgentTeachingSession:
        try:
            return self.multi_agent_teaching_sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Multi-agent teaching session not found: {session_id}") from exc

    def require_whiteboard_session(self, session_id: str) -> WhiteboardSession:
        try:
            return self.whiteboard_sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Whiteboard session not found: {session_id}") from exc

    def add_quiz(self, quiz: Quiz) -> Quiz:
        self.quizzes[quiz.id] = quiz
        for q in quiz.questions:
            self.quiz_questions[q.id] = q
        return quiz

    def require_quiz(self, quiz_id: str) -> Quiz:
        try:
            return self.quizzes[quiz_id]
        except KeyError as exc:
            raise KeyError(f"Quiz not found: {quiz_id}") from exc

    def add_question_paper(self, paper: QuestionPaper) -> QuestionPaper:
        self.question_papers[paper.id] = paper
        return paper

    def require_question_paper(self, paper_id: str) -> QuestionPaper:
        try:
            return self.question_papers[paper_id]
        except KeyError as exc:
            raise KeyError(f"Question paper not found: {paper_id}") from exc

    def add_attempt(self, attempt: Attempt) -> Attempt:
        self.attempts[attempt.id] = attempt
        return attempt

    def require_attempt(self, attempt_id: str) -> Attempt:
        try:
            return self.attempts[attempt_id]
        except KeyError as exc:
            raise KeyError(f"Attempt not found: {attempt_id}") from exc

    def add_answer_key(self, key: AnswerKey) -> AnswerKey:
        self.answer_keys[key.id] = key
        return key

    def require_answer_key(self, key_id: str) -> AnswerKey:
        try:
            return self.answer_keys[key_id]
        except KeyError as exc:
            raise KeyError(f"Answer key not found: {key_id}") from exc

    def add_eval_report(self, report: EvalReport) -> EvalReport:
        self.eval_reports[report.id] = report
        return report

    def require_eval_report(self, report_id: str) -> EvalReport:
        try:
            return self.eval_reports[report_id]
        except KeyError as exc:
            raise KeyError(f"Eval report not found: {report_id}") from exc

    # ── Phase 3: Revision Cards ──────────────────────────────────────────

    def add_revision_card(self, card: RevisionCard) -> RevisionCard:
        self.revision_cards[card.id] = card
        return card

    def require_revision_card(self, card_id: str) -> RevisionCard:
        try:
            return self.revision_cards[card_id]
        except KeyError as exc:
            raise KeyError(f"Revision card not found: {card_id}") from exc

    def save_revision_card(self, card: RevisionCard) -> RevisionCard:
        self.revision_cards[card.id] = card
        return card

    def due_revision_cards(self, user_id: str, today: str) -> list[RevisionCard]:
        return [
            card for card in self.revision_cards.values()
            if card.user_id == user_id and card.due_date <= today
        ]

    def notebook_revision_cards(self, notebook_id: str) -> list[RevisionCard]:
        return [card for card in self.revision_cards.values() if card.notebook_id == notebook_id]

    # ── Phase 3: Sessions ────────────────────────────────────────────────

    def add_session(self, session: Session) -> Session:
        self.sessions[session.id] = session
        return session

    def require_session(self, session_id: str) -> Session:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Session not found: {session_id}") from exc

    def user_sessions(self, user_id: str, notebook_id: str | None = None) -> list[Session]:
        matching = [s for s in self.sessions.values() if s.user_id == user_id]
        if notebook_id:
            matching = [s for s in matching if s.notebook_id == notebook_id]
        return sorted(matching, key=lambda s: s.started_at, reverse=True)

    # ── Phase 3: Student Profile & Mastery ───────────────────────────────

    def add_student_profile(self, profile: StudentProfile) -> StudentProfile:
        self.student_profiles[profile.id] = profile
        return profile

    def require_student_profile(self, profile_id: str) -> StudentProfile:
        try:
            return self.student_profiles[profile_id]
        except KeyError as exc:
            raise KeyError(f"Student profile not found: {profile_id}") from exc

    def student_profile_for(self, user_id: str, notebook_id: str) -> StudentProfile | None:
        for p in self.student_profiles.values():
            if p.user_id == user_id and p.notebook_id == notebook_id:
                return p
        return None

    def add_topic_mastery(self, mastery: TopicMastery) -> TopicMastery:
        self.topic_masteries[mastery.id] = mastery
        return mastery

    def topic_masteries_for(self, profile_id: str) -> list[TopicMastery]:
        return [m for m in self.topic_masteries.values() if m.student_profile_id == profile_id]

    def clear_topic_masteries(self, profile_id: str) -> None:
        ids = [m.id for m in self.topic_masteries.values() if m.student_profile_id == profile_id]
        for mid in ids:
            del self.topic_masteries[mid]

    # ── Phase 4: Pricing & economics ─────────────────────────────────────

    def add_subscription(self, subscription: Subscription) -> Subscription:
        self.subscriptions[subscription.id] = subscription
        return subscription

    def save_subscription(self, subscription: Subscription) -> Subscription:
        self.subscriptions[subscription.id] = subscription
        return subscription

    def subscription_for(self, user_id: str) -> Subscription | None:
        matching = [s for s in self.subscriptions.values() if s.user_id == user_id]
        if not matching:
            return None
        return sorted(matching, key=lambda s: s.created_at)[-1]

    def add_usage_record(self, record: UsageRecord) -> UsageRecord:
        self.usage_records[record.id] = record
        return record

    def usage_for_period(self, user_id: str, billing_period: str) -> list[UsageRecord]:
        return [
            r for r in self.usage_records.values()
            if r.user_id == user_id and r.billing_period == billing_period
        ]

    def to_plain(self, value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, list):
            return [self.to_plain(item) for item in value]
        if isinstance(value, dict):
            return {key: self.to_plain(item) for key, item in value.items()}
        return value
