from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import SqliteStudyLabStore, StudyLabAPI  # noqa: E402

SAMPLE = (
    "Gradient descent moves opposite the gradient of the loss. "
    "Theta := theta - eta * gradient. The learning rate controls step size."
)


class _EnvGuard:
    def __init__(self, **values: str) -> None:
        self.values = values
        self._saved: dict[str, str | None] = {}

    def __enter__(self):
        for k, v in self.values.items():
            self._saved[k] = os.environ.get(k)
            os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _full_class_setup(api: StudyLabAPI) -> dict:
    """Build a full class with one student submitting to one assignment."""
    with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
        boss = api.register_user("boss@x.com", "password0")["user"]
    instructor = api.register_user("teach@x.com", "password1")["user"]
    api.set_user_role(boss["id"], instructor["id"], "instructor")
    student = api.register_user("kid@x.com", "password2")["user"]
    nb = api.create_notebook("ML", user_id=instructor["id"])
    api.upload_source(nb["id"], "Notes", SAMPLE)
    quiz = api.generate_quiz(nb["id"], num_questions=2)
    cls = api.create_class(instructor["id"], "ML 101")
    api.enroll_in_class(student["id"], cls["code"])
    assignment = api.create_assignment(
        instructor_id=instructor["id"],
        class_id=cls["id"],
        kind="quiz",
        source_id=quiz["id"],
        title="HW 1",
    )
    submit = api.submit_assignment(student["id"], assignment["id"], [])
    return {
        "instructor": instructor,
        "student": student,
        "boss": boss,
        "notebook": nb,
        "quiz": quiz,
        "class": cls,
        "assignment": assignment,
        "submission": submit["submission"],
        "attempt": submit["attempt"],
    }


# ── Notebook comments ──────────────────────────────────────────────────────

class Phase9CommentTests(unittest.TestCase):
    def test_owner_can_post_and_list_comments(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        comment = api.post_notebook_comment(owner["id"], nb["id"], "First thought")
        self.assertEqual(comment["body"], "First thought")
        listed = api.list_notebook_comments(owner["id"], nb["id"])
        self.assertEqual(len(listed["comments"]), 1)
        self.assertEqual(listed["comments"][0]["author_email"], "owner@x.com")

    def test_shared_viewer_can_comment(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        viewer = api.register_user("viewer@x.com", "password2")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        api.post_notebook_comment(viewer["id"], nb["id"], "hi from a viewer")
        listed = api.list_notebook_comments(owner["id"], nb["id"])
        self.assertEqual(len(listed["comments"]), 1)

    def test_stranger_cannot_comment_or_read(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        stranger = api.register_user("nope@x.com", "password2")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        with self.assertRaises(PermissionError):
            api.post_notebook_comment(stranger["id"], nb["id"], "sneak")
        with self.assertRaises(PermissionError):
            api.list_notebook_comments(stranger["id"], nb["id"])

    def test_empty_body_rejected(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        with self.assertRaises(ValueError):
            api.post_notebook_comment(owner["id"], nb["id"], "   ")

    def test_comment_emits_notification_to_others(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        viewer = api.register_user("viewer@x.com", "password2")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        # Clear the share notification first.
        api.mark_all_notifications_read(viewer["id"])
        api.post_notebook_comment(owner["id"], nb["id"], "hello")
        viewer_inbox = api.list_notifications(viewer["id"], unread_only=True)
        self.assertEqual(viewer_inbox["unread_count"], 1)
        self.assertEqual(viewer_inbox["notifications"][0]["kind"], "comment_posted")
        # Author should NOT receive a notification for their own comment.
        author_inbox = api.list_notifications(owner["id"], unread_only=True)
        self.assertTrue(all(n["kind"] != "comment_posted" for n in author_inbox["notifications"]))


# ── Submission feedback ────────────────────────────────────────────────────

class Phase9FeedbackTests(unittest.TestCase):
    def test_instructor_adds_feedback_and_student_sees_it(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        api.add_submission_feedback(
            ctx["instructor"]["id"], ctx["submission"]["id"], "good effort, revise gradient descent"
        )
        fb = api.get_submission_feedback(ctx["student"]["id"], ctx["submission"]["id"])
        self.assertIn("revise gradient descent", fb["feedback"])

    def test_non_instructor_cannot_grade(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        with self.assertRaises(PermissionError):
            api.add_submission_feedback(ctx["student"]["id"], ctx["submission"]["id"], "self-grade")

    def test_stranger_cannot_read_feedback(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        api.add_submission_feedback(ctx["instructor"]["id"], ctx["submission"]["id"], "ok")
        stranger = api.register_user("nope@x.com", "password9")["user"]
        with self.assertRaises(PermissionError):
            api.get_submission_feedback(stranger["id"], ctx["submission"]["id"])

    def test_override_score_replaces_auto_in_listing(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        max_score = ctx["attempt"]["max_score"]
        api.add_submission_feedback(
            ctx["instructor"]["id"], ctx["submission"]["id"], "credit for effort", override_score=max_score
        )
        listed = api.list_assignment_submissions(ctx["instructor"]["id"], ctx["assignment"]["id"])
        row = listed["submissions"][0]
        self.assertEqual(row["total_score"], max_score)
        self.assertEqual(row["auto_score"], 0.0)
        self.assertTrue(row["has_feedback"])

    def test_override_out_of_range_rejected(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        max_score = ctx["attempt"]["max_score"]
        with self.assertRaises(ValueError):
            api.add_submission_feedback(
                ctx["instructor"]["id"], ctx["submission"]["id"], "too generous", override_score=max_score + 1
            )

    def test_feedback_emits_student_notification(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        api.mark_all_notifications_read(ctx["student"]["id"])
        api.add_submission_feedback(ctx["instructor"]["id"], ctx["submission"]["id"], "see me")
        inbox = api.list_notifications(ctx["student"]["id"], unread_only=True)
        self.assertEqual(inbox["unread_count"], 1)
        self.assertEqual(inbox["notifications"][0]["kind"], "submission_graded")


# ── Notifications & emit hooks ────────────────────────────────────────────

class Phase9NotificationTests(unittest.TestCase):
    def test_share_emits_recipient_notification(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        target = api.register_user("t@x.com", "password2")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "t@x.com", "viewer")
        inbox = api.list_notifications(target["id"])
        self.assertGreaterEqual(inbox["unread_count"], 1)
        self.assertTrue(any(n["kind"] == "notebook_shared" for n in inbox["notifications"]))

    def test_assignment_creation_notifies_every_enrolled_student(self) -> None:
        api = StudyLabAPI()
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            boss = api.register_user("boss@x.com", "password0")["user"]
        instructor = api.register_user("teach@x.com", "password1")["user"]
        api.set_user_role(boss["id"], instructor["id"], "instructor")
        nb = api.create_notebook("ML", user_id=instructor["id"])
        api.upload_source(nb["id"], "Notes", SAMPLE)
        quiz = api.generate_quiz(nb["id"], num_questions=2)
        cls = api.create_class(instructor["id"], "ML")
        student_a = api.register_user("a@x.com", "password2")["user"]
        student_b = api.register_user("b@x.com", "password3")["user"]
        api.enroll_in_class(student_a["id"], cls["code"])
        api.enroll_in_class(student_b["id"], cls["code"])
        api.create_assignment(
            instructor_id=instructor["id"], class_id=cls["id"], kind="quiz",
            source_id=quiz["id"], title="HW",
        )
        for s in (student_a, student_b):
            inbox = api.list_notifications(s["id"], unread_only=True)
            self.assertTrue(any(n["kind"] == "assignment_created" for n in inbox["notifications"]))

    def test_enroll_notifies_instructor_and_submit_notifies_too(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        inbox = api.list_notifications(ctx["instructor"]["id"], unread_only=True)
        kinds = {n["kind"] for n in inbox["notifications"]}
        self.assertIn("class_enrolled", kinds)
        self.assertIn("submission_received", kinds)

    def test_user_cannot_mark_others_notifications(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        target = api.register_user("t@x.com", "password2")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "t@x.com", "viewer")
        notif_id = api.list_notifications(target["id"])["notifications"][0]["id"]
        with self.assertRaises(PermissionError):
            api.mark_notification_read(owner["id"], notif_id)

    def test_mark_all_read_zeroes_unread(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        api.mark_all_notifications_read(ctx["instructor"]["id"])
        self.assertEqual(api.list_notifications(ctx["instructor"]["id"], unread_only=True)["unread_count"], 0)


# ── Persistence + cascade ──────────────────────────────────────────────────

class Phase9PersistenceTests(unittest.TestCase):
    def test_phase9_data_survives_reopen(self) -> None:
        path = str(Path(tempfile.mkdtemp()) / "p9.db")
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI(SqliteStudyLabStore(path))
            ctx = _full_class_setup(api)
            api.post_notebook_comment(ctx["instructor"]["id"], ctx["notebook"]["id"], "thread")
            api.add_submission_feedback(ctx["instructor"]["id"], ctx["submission"]["id"], "well done")
            api.store.close()

            reopened = StudyLabAPI(SqliteStudyLabStore(path))
            comments = reopened.list_notebook_comments(ctx["instructor"]["id"], ctx["notebook"]["id"])
            self.assertEqual(len(comments["comments"]), 1)
            fb = reopened.get_submission_feedback(ctx["student"]["id"], ctx["submission"]["id"])
            self.assertIn("well done", fb["feedback"])
            inbox = reopened.list_notifications(ctx["student"]["id"])
            self.assertGreater(inbox["unread_count"], 0)
            reopened.store.close()

    def test_deleting_notebook_owner_drops_comments(self) -> None:
        api = StudyLabAPI()
        owner = api.register_user("owner@x.com", "password1")["user"]
        viewer = api.register_user("viewer@x.com", "password2")["user"]
        nb = api.create_notebook("N", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        api.post_notebook_comment(viewer["id"], nb["id"], "msg")
        api.delete_account(owner["id"])
        # Notebook is gone; comments cascaded.
        self.assertEqual(list(api.store.comments.values()), [])

    def test_deleting_student_drops_their_submission_feedback(self) -> None:
        api = StudyLabAPI()
        ctx = _full_class_setup(api)
        api.add_submission_feedback(ctx["instructor"]["id"], ctx["submission"]["id"], "ok")
        api.delete_account(ctx["student"]["id"])
        # Student's submission is gone, and so is the feedback row on it.
        self.assertEqual(
            [f for f in api.store.submission_feedback.values() if f.submission_id == ctx["submission"]["id"]],
            [],
        )


if __name__ == "__main__":
    unittest.main()
