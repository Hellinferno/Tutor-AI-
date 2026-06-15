from __future__ import annotations

from typing import Any

from .models import Comment, Notification, NotificationKind, SubmissionFeedback
from .store import InMemoryStudyLabStore


_MAX_BODY = 8000      # comment body cap (covers a reasonable post; bigger goes to artifacts)
_MAX_FEEDBACK = 8000  # feedback cap


class SocialEngine:
    """Phase 9: discussions, instructor feedback on submissions, and notifications.

    - **Comments** live on a notebook. Any user with notebook access (owner or shared
      viewer/editor) can read or post. Threaded via optional `parent_id`.
    - **Submission feedback** is written by the class instructor (or admin) on a
      `AssignmentSubmission`. Setting `override_score` replaces the auto-graded
      total when computing the final percentage. The student gets a notification.
    - **Notifications** are simple inbox rows scoped to a user. Other engines call
      ``emit_*`` helpers (or ``_notify``) when something they should know about
      happens — share, enrollment, assignment, submission, grading, new comment.

    Notifications are *best-effort*: they never block the originating action. If a
    notification fails to write, the action still succeeds.
    """

    def __init__(self, store: InMemoryStudyLabStore) -> None:
        self.store = store

    # ── Notebook comments ───────────────────────────────────────────────

    def post_comment(
        self,
        author_id: str,
        notebook_id: str,
        body: str,
        parent_id: str | None = None,
    ) -> Comment:
        body = (body or "").strip()
        if not body:
            raise ValueError("comment body must not be empty")
        if len(body) > _MAX_BODY:
            raise ValueError(f"comment body exceeds the maximum of {_MAX_BODY} characters")
        self.store.require_user(author_id)
        notebook = self.store.require_notebook(notebook_id)
        if parent_id is not None:
            parent = self.store.require_comment(parent_id)
            if parent.notebook_id != notebook_id:
                raise ValueError("parent comment belongs to a different notebook")
        comment = Comment(
            id=self.store.next_id("cmt"),
            notebook_id=notebook_id,
            author_id=author_id,
            body=body,
            parent_id=parent_id,
        )
        self.store.add_comment(comment)
        # Notify the notebook owner + every shared user, except the author.
        recipients: set[str] = {notebook.user_id}
        recipients.update(share.shared_with_id for share in self.store.shares_for_notebook(notebook_id))
        recipients.discard(author_id)
        author = self.store.users.get(author_id)
        for uid in recipients:
            self._notify(uid, "comment_posted", {
                "notebook_id": notebook_id,
                "notebook_title": notebook.title,
                "author_id": author_id,
                "author_email": getattr(author, "email", None),
                "comment_id": comment.id,
                "preview": body[:160],
            })
        return comment

    def list_comments(self, notebook_id: str) -> list[Comment]:
        self.store.require_notebook(notebook_id)
        return self.store.comments_for_notebook(notebook_id)

    # ── Submission feedback ─────────────────────────────────────────────

    def add_feedback(
        self,
        instructor_id: str,
        submission_id: str,
        feedback_text: str,
        override_score: float | None = None,
    ) -> SubmissionFeedback:
        feedback_text = (feedback_text or "").strip()
        if not feedback_text:
            raise ValueError("feedback must not be empty")
        if len(feedback_text) > _MAX_FEEDBACK:
            raise ValueError(f"feedback exceeds the maximum of {_MAX_FEEDBACK} characters")
        submission = self.store.require_submission(submission_id)
        assignment = self.store.require_assignment(submission.assignment_id)
        cls = self.store.require_class(assignment.class_id)
        if cls.instructor_id != instructor_id:
            user = self.store.users.get(instructor_id)
            if user is None or user.role != "admin":
                raise PermissionError("only the class's instructor (or admin) can add feedback")
        if override_score is not None:
            attempt = self.store.attempts.get(submission.attempt_id)
            max_score = float(getattr(attempt, "max_score", 0.0))
            if override_score < 0 or override_score > max_score:
                raise ValueError(
                    f"override_score must be in [0, {max_score}]"
                )
        feedback = SubmissionFeedback(
            id=self.store.next_id("fbk"),
            submission_id=submission_id,
            instructor_id=instructor_id,
            feedback=feedback_text,
            override_score=override_score,
        )
        self.store.add_submission_feedback(feedback)
        # Notify the student.
        self._notify(submission.student_id, "submission_graded", {
            "assignment_id": assignment.id,
            "assignment_title": assignment.title,
            "class_id": cls.id,
            "class_name": cls.name,
            "submission_id": submission.id,
            "override_score": override_score,
            "preview": feedback_text[:160],
        })
        return feedback

    def get_feedback(self, requester_id: str, submission_id: str) -> SubmissionFeedback | None:
        submission = self.store.require_submission(submission_id)
        assignment = self.store.require_assignment(submission.assignment_id)
        cls = self.store.require_class(assignment.class_id)
        if requester_id != submission.student_id and requester_id != cls.instructor_id:
            user = self.store.users.get(requester_id)
            if user is None or user.role != "admin":
                raise PermissionError("only the student or the class's instructor can read this feedback")
        return self.store.feedback_for_submission(submission_id)

    # ── Notifications ───────────────────────────────────────────────────

    def list_notifications(self, user_id: str, unread_only: bool = False) -> dict[str, Any]:
        self.store.require_user(user_id)
        rows = self.store.notifications_for_user(user_id, unread_only=unread_only)
        unread = sum(1 for n in rows if n.read_at is None) if not unread_only else len(rows)
        return {
            "notifications": [self.store.to_plain(n) for n in rows],
            "unread_count": unread,
        }

    def mark_read(self, user_id: str, notification_id: str) -> dict[str, Any]:
        notif = self.store.require_notification(notification_id)
        if notif.user_id != user_id:
            raise PermissionError("you cannot mark someone else's notification as read")
        if notif.read_at is None:
            self.store.mark_notifications_read(user_id, ids=[notification_id])
        # Re-read to get the updated timestamp.
        notif = self.store.require_notification(notification_id)
        return self.store.to_plain(notif)

    def mark_all_read(self, user_id: str) -> dict[str, Any]:
        self.store.require_user(user_id)
        updated = self.store.mark_notifications_read(user_id)
        return {"ok": True, "marked_read": updated}

    # ── Notification emitters (called by other engines) ───────────────────

    def emit_notebook_shared(self, owner_id: str, recipient_id: str, notebook_id: str, role: str) -> None:
        notebook = self.store.notebooks.get(notebook_id)
        owner = self.store.users.get(owner_id)
        self._notify(recipient_id, "notebook_shared", {
            "notebook_id": notebook_id,
            "notebook_title": getattr(notebook, "title", None),
            "owner_id": owner_id,
            "owner_email": getattr(owner, "email", None),
            "role": role,
        })

    def emit_class_enrolled(self, instructor_id: str, student_id: str, class_id: str) -> None:
        cls = self.store.classes.get(class_id)
        student = self.store.users.get(student_id)
        self._notify(instructor_id, "class_enrolled", {
            "class_id": class_id,
            "class_name": getattr(cls, "name", None),
            "student_id": student_id,
            "student_email": getattr(student, "email", None),
        })

    def emit_assignment_created(self, instructor_id: str, class_id: str, assignment_id: str) -> int:
        cls = self.store.classes.get(class_id)
        assignment = self.store.assignments.get(assignment_id)
        if cls is None or assignment is None:
            return 0
        n = 0
        for enrollment in self.store.enrollments_for_class(class_id):
            self._notify(enrollment.student_id, "assignment_created", {
                "class_id": class_id,
                "class_name": cls.name,
                "assignment_id": assignment.id,
                "assignment_title": assignment.title,
                "kind": assignment.kind,
                "due_at": assignment.due_at,
            })
            n += 1
        return n

    def emit_submission_received(self, instructor_id: str, student_id: str, assignment_id: str, submission_id: str) -> None:
        assignment = self.store.assignments.get(assignment_id)
        student = self.store.users.get(student_id)
        if assignment is None:
            return
        cls = self.store.classes.get(assignment.class_id)
        self._notify(instructor_id, "submission_received", {
            "class_id": assignment.class_id,
            "class_name": getattr(cls, "name", None),
            "assignment_id": assignment.id,
            "assignment_title": assignment.title,
            "student_id": student_id,
            "student_email": getattr(student, "email", None),
            "submission_id": submission_id,
        })

    # ── helpers ─────────────────────────────────────────────────────────

    def _notify(self, user_id: str, kind: NotificationKind, payload: dict[str, Any]) -> Notification | None:
        if not user_id:
            return None
        # Best-effort: the originating action must not fail because of a notification.
        try:
            notification = Notification(
                id=self.store.next_id("notif"),
                user_id=user_id,
                kind=kind,
                payload=payload,
            )
            return self.store.add_notification(notification)
        except Exception:
            return None
