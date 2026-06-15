from __future__ import annotations

import secrets
from statistics import mean
from typing import Any

from .eval import EvalEngine
from .models import (
    Assignment,
    AssignmentKind,
    AssignmentSubmission,
    Class,
    ClassEnrollment,
)
from .store import InMemoryStudyLabStore


_JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # ambiguity-safe
_JOIN_CODE_LEN = 6


class ClassroomEngine:
    """Phase 8: classrooms, assignments, and class analytics.

    A class is owned by an instructor (role ``instructor`` or ``admin``). Students
    enroll via a short join code. An assignment points at an existing quiz or paper
    in the instructor's notebook; students submit through the standard eval engine
    and submissions are linked back to the assignment so the instructor can see
    class-wide results.
    """

    def __init__(self, store: InMemoryStudyLabStore, eval_engine: EvalEngine) -> None:
        self.store = store
        self.eval = eval_engine

    # ── Class CRUD ──────────────────────────────────────────────────────

    def create_class(self, instructor_id: str, name: str) -> Class:
        instructor = self.store.require_user(instructor_id)
        if instructor.role not in ("instructor", "admin"):
            raise PermissionError("only instructors (or admins) can create classes")
        if not name or not name.strip():
            raise ValueError("class name must not be empty")
        code = self._mint_code()
        cls = Class(
            id=self.store.next_id("class"),
            instructor_id=instructor_id,
            name=name.strip(),
            code=code,
        )
        return self.store.add_class(cls)

    def get_class(self, class_id: str) -> Class:
        return self.store.require_class(class_id)

    def list_my_classes(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        instructor_classes = [
            self.store.to_plain(c)
            for c in self.store.all_classes()
            if c.instructor_id == user_id
        ]
        enrolled_ids = {e.class_id for e in self.store.enrollments_for_user(user_id)}
        enrolled = []
        for cls in self.store.all_classes():
            if cls.id not in enrolled_ids:
                continue
            enrolled.append(
                {
                    "id": cls.id,
                    "name": cls.name,
                    "instructor_id": cls.instructor_id,
                    # Students don't get the join code — only the instructor does.
                    "joined_at": next(
                        (e.joined_at for e in self.store.enrollments_for_class(cls.id) if e.student_id == user_id),
                        cls.created_at,
                    ),
                }
            )
        return {"teaching": instructor_classes, "enrolled": enrolled}

    # ── Enrollment ──────────────────────────────────────────────────────

    def enroll(self, student_id: str, code: str) -> dict[str, Any]:
        if not code:
            raise ValueError("join code is required")
        cls = self.store.class_by_code(code.strip().upper())
        if cls is None:
            raise KeyError(f"No class with join code: {code}")
        if cls.instructor_id == student_id:
            raise ValueError("instructors cannot enroll in their own class")
        existing = next(
            (e for e in self.store.enrollments_for_class(cls.id) if e.student_id == student_id),
            None,
        )
        if existing is not None:
            return self.store.to_plain(existing)
        enrollment = ClassEnrollment(
            id=self.store.next_id("enroll"),
            class_id=cls.id,
            student_id=student_id,
        )
        return self.store.to_plain(self.store.add_enrollment(enrollment))

    def list_roster(self, instructor_id: str, class_id: str) -> dict[str, Any]:
        cls = self._require_instructor_class(instructor_id, class_id)
        roster = []
        for e in self.store.enrollments_for_class(cls.id):
            student = self.store.users.get(e.student_id)
            roster.append(
                {
                    "enrollment_id": e.id,
                    "student_id": e.student_id,
                    "email": getattr(student, "email", None),
                    "joined_at": e.joined_at,
                }
            )
        return {
            "class": self.store.to_plain(cls),
            "roster": sorted(roster, key=lambda r: r["joined_at"]),
        }

    # ── Assignments ─────────────────────────────────────────────────────

    def create_assignment(
        self,
        instructor_id: str,
        class_id: str,
        kind: AssignmentKind,
        source_id: str,
        title: str,
        due_at: str | None = None,
    ) -> Assignment:
        cls = self._require_instructor_class(instructor_id, class_id)
        if kind not in ("quiz", "paper"):
            raise ValueError("assignment kind must be 'quiz' or 'paper'")
        if kind == "quiz":
            quiz = self.store.require_quiz(source_id)
            notebook_id = quiz.notebook_id
        else:
            paper = self.store.require_question_paper(source_id)
            notebook_id = paper.notebook_id
        notebook = self.store.require_notebook(notebook_id)
        if notebook.user_id != instructor_id:
            raise PermissionError("you can only assign quizzes/papers from your own notebooks")
        if not title or not title.strip():
            raise ValueError("assignment title must not be empty")
        assignment = Assignment(
            id=self.store.next_id("assign"),
            class_id=cls.id,
            kind=kind,
            source_id=source_id,
            title=title.strip(),
            due_at=due_at,
        )
        return self.store.add_assignment(assignment)

    def list_assignments_for_class(self, user_id: str, class_id: str) -> dict[str, Any]:
        cls = self.store.require_class(class_id)
        if not self._user_can_view_class(user_id, cls):
            raise PermissionError("you are not enrolled in this class")
        assignments = self.store.assignments_for_class(class_id)
        return {
            "class": self.store.to_plain(cls),
            "assignments": [
                self._assignment_with_status(a, user_id, is_instructor=cls.instructor_id == user_id)
                for a in assignments
            ],
        }

    def list_assignments_for_student(self, student_id: str) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for enrollment in self.store.enrollments_for_user(student_id):
            cls = self.store.classes.get(enrollment.class_id)
            if cls is None:
                continue
            for a in self.store.assignments_for_class(cls.id):
                items.append(
                    {
                        **self._assignment_with_status(a, student_id, is_instructor=False),
                        "class_name": cls.name,
                    }
                )
        items.sort(key=lambda x: (x.get("due_at") or "", x["created_at"]))
        return {"assignments": items}

    def submit_assignment(
        self,
        student_id: str,
        assignment_id: str,
        answers: list[dict],
    ) -> dict[str, Any]:
        assignment = self.store.require_assignment(assignment_id)
        cls = self.store.require_class(assignment.class_id)
        if not any(e.student_id == student_id for e in self.store.enrollments_for_class(cls.id)):
            raise PermissionError("you are not enrolled in this class")
        attempt = self.eval.evaluate_attempt(
            source_id=assignment.source_id,
            source_type=assignment.kind,
            user_answers=answers,
            user_id=student_id,
        )
        submission = AssignmentSubmission(
            id=self.store.next_id("subm"),
            assignment_id=assignment.id,
            student_id=student_id,
            attempt_id=attempt.id,
        )
        self.store.add_submission(submission)
        return {
            "submission": self.store.to_plain(submission),
            "attempt": self.store.to_plain(attempt),
        }

    def list_submissions(self, instructor_id: str, assignment_id: str) -> dict[str, Any]:
        assignment = self.store.require_assignment(assignment_id)
        cls = self._require_instructor_class(instructor_id, assignment.class_id)
        rows: list[dict[str, Any]] = []
        for sub in self.store.submissions_for_assignment(assignment_id):
            attempt = self.store.attempts.get(sub.attempt_id)
            student = self.store.users.get(sub.student_id)
            rows.append(
                {
                    "submission_id": sub.id,
                    "student_id": sub.student_id,
                    "email": getattr(student, "email", None),
                    "submitted_at": sub.submitted_at,
                    "total_score": getattr(attempt, "total_score", 0.0),
                    "max_score": getattr(attempt, "max_score", 0.0),
                    "attempt_id": sub.attempt_id,
                }
            )
        return {
            "class": self.store.to_plain(cls),
            "assignment": self.store.to_plain(assignment),
            "submissions": sorted(rows, key=lambda r: r["submitted_at"]),
        }

    # ── Analytics ───────────────────────────────────────────────────────

    def class_analytics(self, instructor_id: str, class_id: str) -> dict[str, Any]:
        cls = self._require_instructor_class(instructor_id, class_id)
        roster = self.store.enrollments_for_class(cls.id)
        assignments = self.store.assignments_for_class(cls.id)
        student_ids = {e.student_id for e in roster}
        per_assignment: list[dict[str, Any]] = []
        weak_topic_counter: dict[str, int] = {}

        for a in assignments:
            subs = self.store.submissions_for_assignment(a.id)
            unique_students = {s.student_id for s in subs}
            scored: list[float] = []
            for s in subs:
                attempt = self.store.attempts.get(s.attempt_id)
                if attempt is None or attempt.max_score <= 0:
                    continue
                scored.append(round(attempt.total_score / attempt.max_score * 100, 1))
                try:
                    report = self.eval.generate_report(s.attempt_id)
                    for t in report.weak_topics:
                        weak_topic_counter[t] = weak_topic_counter.get(t, 0) + 1
                except Exception:
                    pass
            per_assignment.append(
                {
                    "assignment_id": a.id,
                    "title": a.title,
                    "kind": a.kind,
                    "due_at": a.due_at,
                    "submitted_count": len(unique_students),
                    "enrolled_count": len(student_ids),
                    "completion_rate": round(len(unique_students) / max(len(student_ids), 1) * 100, 1),
                    "avg_percentage": round(mean(scored), 1) if scored else None,
                }
            )

        all_scores = [row["avg_percentage"] for row in per_assignment if row["avg_percentage"] is not None]
        weak_topics = sorted(weak_topic_counter, key=lambda k: -weak_topic_counter[k])[:5]
        return {
            "class": self.store.to_plain(cls),
            "enrolled_count": len(student_ids),
            "assignment_count": len(assignments),
            "overall_avg_percentage": round(mean(all_scores), 1) if all_scores else None,
            "per_assignment": per_assignment,
            "top_weak_topics": weak_topics,
        }

    # ── helpers ─────────────────────────────────────────────────────────

    def _require_instructor_class(self, instructor_id: str, class_id: str) -> Class:
        cls = self.store.require_class(class_id)
        if cls.instructor_id != instructor_id:
            user = self.store.users.get(instructor_id)
            if user is None or user.role != "admin":
                raise PermissionError("only the class's instructor (or admin) can do this")
        return cls

    def _user_can_view_class(self, user_id: str, cls: Class) -> bool:
        if cls.instructor_id == user_id:
            return True
        user = self.store.users.get(user_id)
        if user is not None and user.role == "admin":
            return True
        return any(e.student_id == user_id for e in self.store.enrollments_for_class(cls.id))

    def _assignment_with_status(self, assignment: Assignment, user_id: str, is_instructor: bool) -> dict[str, Any]:
        plain = self.store.to_plain(assignment)
        if is_instructor:
            subs = self.store.submissions_for_assignment(assignment.id)
            plain["submission_count"] = len({s.student_id for s in subs})
            return plain
        sub = next(
            (s for s in self.store.submissions_for_assignment(assignment.id) if s.student_id == user_id),
            None,
        )
        if sub is None:
            plain["submitted"] = False
            return plain
        attempt = self.store.attempts.get(sub.attempt_id)
        plain["submitted"] = True
        plain["submitted_at"] = sub.submitted_at
        plain["attempt_id"] = sub.attempt_id
        plain["total_score"] = getattr(attempt, "total_score", 0.0)
        plain["max_score"] = getattr(attempt, "max_score", 0.0)
        return plain

    def _mint_code(self, attempts: int = 8) -> str:
        for _ in range(attempts):
            code = "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LEN))
            if self.store.class_by_code(code) is None:
                return code
        raise RuntimeError("failed to mint a unique class join code")
