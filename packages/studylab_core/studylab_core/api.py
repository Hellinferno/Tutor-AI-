from __future__ import annotations

import os
from typing import Any

from .analytics import AnalyticsEngine
from .artifacts import ArtifactGenerator
from .auth import AuthEngine
from .classrooms import ClassroomEngine
from .connectors import SourceConnectorEngine
from .eval import EvalEngine
from .metrics import MetricsCollector
from .models import (
    ArtifactType,
    AssignmentKind,
    AttemptSourceType,
    ConnectorType,
    MeteredAction,
    NotebookShare,
    PlanTier,
    RoleType,
    Session,
)
from .notion import NotionExporter
from .ocr import extract_text_from_image_payload
from .paper import PaperEngine
from .pricing import BillingProvider, PricingEngine
from .quiz import QuizEngine
from .rag import RagEngine
from .revision import RepetitionEngine
from .solver import SolverEngine
from .store import InMemoryStudyLabStore
from .student import StudentModel
from .teaching import TeachingEngine
from .voice import VoiceProvider, make_voice_provider


class StudyLabAPI:
    def __init__(
        self,
        store: InMemoryStudyLabStore | None = None,
        voice: VoiceProvider | None = None,
        billing: BillingProvider | None = None,
    ) -> None:
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
        # Phase 4 engines
        self.connectors = SourceConnectorEngine(self.store, self.rag)
        self.pricing = PricingEngine(self.store, billing=billing)
        # Phase 5 engines (production readiness: auth + observability)
        self.auth = AuthEngine(self.store)
        self.metrics = MetricsCollector()
        # Phase 8 engine (classrooms, assignments, class analytics)
        self.classrooms = ClassroomEngine(self.store, self.eval)

    def create_notebook(self, title: str, user_id: str = "demo-user") -> dict[str, Any]:
        return self.store.to_plain(self.rag.create_notebook(title=title, user_id=user_id))

    def upload_source(self, notebook_id: str, title: str, text: str, kind: str = "notes") -> dict[str, Any]:
        self._check_source_size(text)
        source, guide = self.rag.ingest_source(notebook_id=notebook_id, title=title, text=text, kind=kind)
        return {"source": self.store.to_plain(source), "source_guide": self.store.to_plain(guide)}

    def get_source(self, source_id: str) -> dict[str, Any]:
        source = self.store.require_source(source_id)
        guide = self.store.guides.get(source_id)
        return {"source": self.store.to_plain(source), "source_guide": self.store.to_plain(guide)}

    def ask_notebook(self, notebook_id: str, query: str) -> dict[str, Any]:
        result = self.store.to_plain(self.rag.ask(notebook_id=notebook_id, query=query))
        self.metrics.record_ask(
            grounded=result.get("grounding") == "from_sources",
            citation_count=len(result.get("citations") or []),
        )
        return result

    def solve(
        self,
        content: str,
        subject: str = "ai_ds",
        input_type: str = "text",
        notebook_id: str | None = None,
    ) -> dict[str, Any]:
        question = extract_text_from_image_payload(content) if input_type == "image" else content
        result = self.store.to_plain(self.solver.solve(question=question, subject=subject, notebook_id=notebook_id))
        self.metrics.record_solve(
            verified=bool(result.get("verified")),
            from_cache=bool(result.get("from_cache")),
            latency_ms=int(result.get("latency_ms") or 0),
        )
        return result

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
        self.metrics.record_notion_export(ok=bool(getattr(result, "connected", False)))
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

    # ── Phase 4: Multi-agent teaching ─────────────────────────────────────

    def start_multi_agent_teaching(self, notebook_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.start_multi_agent_session(notebook_id))

    def get_multi_agent_session(self, session_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.get_multi_agent_session(session_id))

    def multi_agent_next(self, session_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.multi_agent_next(session_id))

    def multi_agent_prev(self, session_id: str) -> dict[str, Any]:
        return self.store.to_plain(self.teaching.multi_agent_prev(session_id))

    # ── Phase 4: Source connectors ────────────────────────────────────────

    def import_source(
        self,
        notebook_id: str,
        connector_type: ConnectorType,
        title: str,
        payload: dict[str, Any],
        user_id: str = "demo-user",
    ) -> dict[str, Any]:
        self._guard(user_id, "source_import")
        source, guide, record = self.connectors.import_source(
            notebook_id=notebook_id,
            connector_type=connector_type,
            title=title,
            payload=payload,
        )
        return {
            "source": source,
            "source_guide": self.store.to_plain(guide),
            "import": self.store.to_plain(record),
        }

    def list_source_imports(self, notebook_id: str) -> dict[str, Any]:
        imports = [
            self.store.to_plain(record)
            for record in self.store.source_imports.values()
            if record.notebook_id == notebook_id
        ]
        return {"imports": imports, "supported_types": sorted(self.connectors.supported_types)}

    # ── Phase 4: Pricing & economics ──────────────────────────────────────

    def list_plans(self) -> dict[str, Any]:
        return {"plans": [self.store.to_plain(plan) for plan in self.pricing.list_plans()]}

    def get_subscription(self, user_id: str = "demo-user") -> dict[str, Any]:
        return self.store.to_plain(self.pricing.get_subscription(user_id))

    def set_plan(self, user_id: str, tier: PlanTier) -> dict[str, Any]:
        result = self.pricing.set_plan(user_id, tier)
        return {
            "subscription": self.store.to_plain(result["subscription"]),
            "checkout": result["checkout"],
            "plan": self.store.to_plain(result["plan"]),
        }

    def record_usage(self, user_id: str, action: MeteredAction, quantity: int = 1) -> dict[str, Any]:
        return self.store.to_plain(self.pricing.meter(user_id, action, quantity))

    def check_quota(self, user_id: str, action: MeteredAction) -> dict[str, Any]:
        return self.pricing.check_quota(user_id, action)

    def usage_summary(self, user_id: str = "demo-user") -> dict[str, Any]:
        return self.pricing.usage_summary(user_id)

    def enforce_quota(self, user_id: str, action: MeteredAction) -> dict[str, Any]:
        """Explicitly enforce a quota for a metered action (raises QuotaExceededError)."""
        record = self.pricing.enforce(user_id, action)
        return {"recorded": self.store.to_plain(record), "quota": self.pricing.check_quota(user_id, action)}

    def _check_source_size(self, text: str) -> None:
        """Reject oversized source text (production safety cap; default ~1M chars)."""
        cap = _max_source_chars()
        if len(text or "") > cap:
            raise ValueError(f"source text exceeds the maximum of {cap} characters")

    def _guard(self, user_id: str, action: MeteredAction) -> None:
        """Meter a metered action — enforcing the quota when STUDYLAB_ENFORCE_QUOTAS is set.

        Default (flag unset): best-effort metering that never blocks a product action,
        preserving the offline/test experience. Flag set: raises QuotaExceededError when
        the plan quota is exhausted, which the gateway maps to HTTP 402.
        """
        if _truthy(os.getenv("STUDYLAB_ENFORCE_QUOTAS")):
            self.pricing.enforce(user_id, action)
            return
        try:
            self.pricing.meter(user_id, action)
        except Exception:
            pass

    # ── Phase 5: Authentication & authorization ───────────────────────────

    def register_user(self, email: str, password: str, subject_domain: str = "ai_ds") -> dict[str, Any]:
        user = self.auth.register(email=email, password=password, subject_domain=subject_domain)
        return {"user": self.auth.public_user(user), "token": self.auth.issue_token(user), "token_type": "Bearer"}

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self.auth.login(email=email, password=password)

    def current_user(self, token: str) -> dict[str, Any]:
        return self.auth.public_user(self.auth.user_from_token(token))

    def user_id_from_token(self, token: str) -> str:
        return self.auth.user_from_token(token).id

    def authorize_notebook(self, user_id: str, notebook_id: str, require_edit: bool = False) -> bool:
        """Return True if the user may access the notebook; raise PermissionError otherwise.

        Access = the owner, or a user it has been shared with (Phase 7). A `viewer` share
        grants read / ask / generate; an `editor` share also grants writes (`require_edit`).
        """
        notebook = self.store.require_notebook(notebook_id)
        if notebook.user_id == user_id:
            return True
        share = self.store.share_for(notebook_id, user_id)
        if share is None:
            raise PermissionError("you do not have access to this notebook")
        if require_edit and share.role != "editor":
            raise PermissionError("you have view-only access to this notebook")
        return True

    def notebook_id_for_teaching(self, session_id: str) -> str:
        return self.teaching.get_session(session_id).notebook_id

    def notebook_id_for_agent_session(self, session_id: str) -> str:
        return self.teaching.get_multi_agent_session(session_id).notebook_id

    # ── Phase 6: Account self-service ──────────────────────────────────────

    def change_password(self, user_id: str, current_password: str, new_password: str) -> dict[str, Any]:
        return self.auth.change_password(user_id, current_password, new_password)

    def update_profile(self, user_id: str, subject_domain: str | None = None, prefs: dict | None = None) -> dict[str, Any]:
        return self.auth.update_profile(user_id, subject_domain=subject_domain, prefs=prefs)

    def request_password_reset(self, email: str) -> dict[str, Any]:
        return self.auth.request_password_reset(email)

    def reset_password(self, token: str, new_password: str) -> dict[str, Any]:
        return self.auth.reset_password(token, new_password)

    def delete_account(self, user_id: str) -> dict[str, Any]:
        return self.auth.delete_account(user_id)

    # ── Phase 7: Collaboration & sharing ──────────────────────────────────

    def share_notebook(self, owner_id: str, notebook_id: str, email: str, role: str = "viewer") -> dict[str, Any]:
        """Share a notebook owned by `owner_id` with another user (by email)."""
        notebook = self.store.require_notebook(notebook_id)
        if notebook.user_id != owner_id:
            raise PermissionError("only the owner can share this notebook")
        if role not in ("viewer", "editor"):
            raise ValueError("role must be 'viewer' or 'editor'")
        target = self.store.get_user_by_email((email or "").strip().lower())
        if target is None:
            raise KeyError(f"No user with email: {email}")
        if target.id == owner_id:
            raise ValueError("you already own this notebook")
        existing = self.store.share_for(notebook_id, target.id)
        if existing is not None:
            existing.role = role
            self.store.remove_share(existing.id)
            self.store.add_share(existing)
            return self.store.to_plain(existing)
        share = NotebookShare(
            id=self.store.next_id("share"),
            notebook_id=notebook_id,
            owner_id=owner_id,
            shared_with_id=target.id,
            shared_with_email=target.email,
            role=role,
        )
        return self.store.to_plain(self.store.add_share(share))

    def unshare_notebook(self, owner_id: str, notebook_id: str, share_id: str) -> dict[str, Any]:
        notebook = self.store.require_notebook(notebook_id)
        if notebook.user_id != owner_id:
            raise PermissionError("only the owner can manage shares for this notebook")
        # Scope the removal to this notebook so an owner can't delete a share on a
        # notebook they don't own by passing a foreign share_id (IDOR).
        if not any(s.id == share_id for s in self.store.shares_for_notebook(notebook_id)):
            raise KeyError(f"Share not found on this notebook: {share_id}")
        self.store.remove_share(share_id)
        return {"ok": True, "removed": share_id}

    def list_shares(self, owner_id: str, notebook_id: str) -> dict[str, Any]:
        notebook = self.store.require_notebook(notebook_id)
        if notebook.user_id != owner_id:
            raise PermissionError("only the owner can list shares for this notebook")
        return {"shares": [self.store.to_plain(s) for s in self.store.shares_for_notebook(notebook_id)]}

    def list_shared_with_me(self, user_id: str) -> dict[str, Any]:
        items = []
        for share in self.store.shares_for_user(user_id):
            notebook = self.store.notebooks.get(share.notebook_id)
            if notebook is None:
                continue
            items.append({
                "share_id": share.id,
                "notebook_id": share.notebook_id,
                "title": notebook.title,
                "role": share.role,
                "owner_id": share.owner_id,
            })
        return {"shared_with_me": items}

    # ── Phase 7: Roles / admin ────────────────────────────────────────────

    def require_admin(self, user_id: str) -> None:
        user = self.store.require_user(user_id)
        if user.role != "admin":
            raise PermissionError("admin role required")

    def list_users(self, requester_id: str) -> dict[str, Any]:
        self.require_admin(requester_id)
        return {"users": [self.auth.public_user(u) for u in self.store.all_users()]}

    def set_user_role(self, requester_id: str, target_user_id: str, role: RoleType) -> dict[str, Any]:
        """Admin-only: promote or demote a user (used to mint instructors for Phase 8)."""
        self.require_admin(requester_id)
        if role not in ("student", "instructor", "admin"):
            raise ValueError("role must be 'student', 'instructor', or 'admin'")
        user = self.store.require_user(target_user_id)
        user.role = role
        self.store.save_user(user)
        return self.auth.public_user(user)

    # ── Phase 8: Classrooms, assignments, class analytics ─────────────────

    def create_class(self, instructor_id: str, name: str) -> dict[str, Any]:
        return self.store.to_plain(self.classrooms.create_class(instructor_id, name))

    def list_my_classes(self, user_id: str) -> dict[str, Any]:
        return self.classrooms.list_my_classes(user_id)

    def enroll_in_class(self, student_id: str, code: str) -> dict[str, Any]:
        return self.classrooms.enroll(student_id, code)

    def list_class_roster(self, instructor_id: str, class_id: str) -> dict[str, Any]:
        return self.classrooms.list_roster(instructor_id, class_id)

    def create_assignment(
        self,
        instructor_id: str,
        class_id: str,
        kind: AssignmentKind,
        source_id: str,
        title: str,
        due_at: str | None = None,
    ) -> dict[str, Any]:
        return self.store.to_plain(
            self.classrooms.create_assignment(
                instructor_id=instructor_id,
                class_id=class_id,
                kind=kind,
                source_id=source_id,
                title=title,
                due_at=due_at,
            )
        )

    def list_class_assignments(self, user_id: str, class_id: str) -> dict[str, Any]:
        return self.classrooms.list_assignments_for_class(user_id, class_id)

    def list_assignments_for_student(self, student_id: str) -> dict[str, Any]:
        return self.classrooms.list_assignments_for_student(student_id)

    def submit_assignment(
        self,
        student_id: str,
        assignment_id: str,
        answers: list[dict],
    ) -> dict[str, Any]:
        return self.classrooms.submit_assignment(student_id, assignment_id, answers)

    def list_assignment_submissions(self, instructor_id: str, assignment_id: str) -> dict[str, Any]:
        return self.classrooms.list_submissions(instructor_id, assignment_id)

    def class_analytics(self, instructor_id: str, class_id: str) -> dict[str, Any]:
        return self.classrooms.class_analytics(instructor_id, class_id)

    # ── Phase 5: Observability ────────────────────────────────────────────

    def metrics_snapshot(self) -> dict[str, Any]:
        return self.metrics.snapshot()


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _max_source_chars() -> int:
    raw = os.getenv("STUDYLAB_MAX_SOURCE_CHARS")
    try:
        return int(raw) if raw else 1_000_000
    except ValueError:
        return 1_000_000
