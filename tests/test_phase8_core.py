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


def _setup_class_with_quiz(api: StudyLabAPI):
    """Build a class with one assignment pointing at a real quiz."""
    with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
        # Re-register so the admin role takes effect for boss.
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
    return {
        "instructor": instructor,
        "student": student,
        "boss": boss,
        "notebook": nb,
        "quiz": quiz,
        "class": cls,
        "assignment": assignment,
    }


# ── Class creation & roles ─────────────────────────────────────────────────

class Phase8ClassCreationTests(unittest.TestCase):
    def test_only_instructor_can_create_class(self) -> None:
        api = StudyLabAPI()
        student = api.register_user("kid@x.com", "password1")["user"]
        with self.assertRaises(PermissionError):
            api.create_class(student["id"], "Math")

    def test_admin_can_create_class(self) -> None:
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
        cls = api.create_class(boss["id"], "Math")
        self.assertEqual(cls["name"], "Math")
        self.assertEqual(len(cls["code"]), 6)

    def test_admin_sets_user_role(self) -> None:
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
        target = api.register_user("t@x.com", "password2")["user"]
        promoted = api.set_user_role(boss["id"], target["id"], "instructor")
        self.assertEqual(promoted["role"], "instructor")

    def test_non_admin_cannot_set_user_role(self) -> None:
        api = StudyLabAPI()
        a = api.register_user("a@x.com", "password1")["user"]
        b = api.register_user("b@x.com", "password2")["user"]
        with self.assertRaises(PermissionError):
            api.set_user_role(a["id"], b["id"], "instructor")

    def test_set_user_role_rejects_bad_role(self) -> None:
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
        target = api.register_user("t@x.com", "password2")["user"]
        with self.assertRaises(ValueError):
            api.set_user_role(boss["id"], target["id"], "owner")


# ── Enrollment ─────────────────────────────────────────────────────────────

class Phase8EnrollmentTests(unittest.TestCase):
    def test_enroll_with_code_works(self) -> None:
        ctx = _setup_class_with_quiz(StudyLabAPI())
        roster = StudyLabAPI  # noqa
        roster = ctx
        # student already enrolled in setup
        api = StudyLabAPI()
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api.register_user("boss@x.com", "password0")  # mint admin
        instructor = api.register_user("t@x.com", "password1")["user"]
        # Promote via admin
        boss = api.store.get_user_by_email("boss@x.com")
        api.set_user_role(boss.id, instructor["id"], "instructor")
        cls = api.create_class(instructor["id"], "ML")
        student = api.register_user("kid@x.com", "password2")["user"]
        enrollment = api.enroll_in_class(student["id"], cls["code"])
        self.assertEqual(enrollment["student_id"], student["id"])

    def test_enroll_unknown_code_rejected(self) -> None:
        api = StudyLabAPI()
        student = api.register_user("kid@x.com", "password1")["user"]
        with self.assertRaises(KeyError):
            api.enroll_in_class(student["id"], "NOPE99")

    def test_instructor_cannot_enroll_in_own_class(self) -> None:
        ctx = _setup_class_with_quiz(StudyLabAPI())
        api = StudyLabAPI()
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api.register_user("boss@x.com", "password0")
        instructor = api.register_user("t@x.com", "password1")["user"]
        boss = api.store.get_user_by_email("boss@x.com")
        api.set_user_role(boss.id, instructor["id"], "instructor")
        cls = api.create_class(instructor["id"], "ML")
        with self.assertRaises(ValueError):
            api.enroll_in_class(instructor["id"], cls["code"])
        _ = ctx  # silence

    def test_enroll_twice_is_idempotent(self) -> None:
        api = StudyLabAPI()
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api.register_user("boss@x.com", "password0")
        instructor = api.register_user("t@x.com", "password1")["user"]
        boss = api.store.get_user_by_email("boss@x.com")
        api.set_user_role(boss.id, instructor["id"], "instructor")
        cls = api.create_class(instructor["id"], "ML")
        student = api.register_user("kid@x.com", "password2")["user"]
        e1 = api.enroll_in_class(student["id"], cls["code"])
        e2 = api.enroll_in_class(student["id"], cls["code"])
        self.assertEqual(e1["id"], e2["id"])

    def test_roster_visible_only_to_instructor(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        # Non-instructor (student) of the same class cannot see the roster.
        with self.assertRaises(PermissionError):
            api.list_class_roster(ctx["student"]["id"], ctx["class"]["id"])
        # Random stranger also cannot.
        stranger = api.register_user("nope@x.com", "password9")["user"]
        with self.assertRaises(PermissionError):
            api.list_class_roster(stranger["id"], ctx["class"]["id"])


# ── Assignments & submissions ──────────────────────────────────────────────

class Phase8AssignmentTests(unittest.TestCase):
    def test_create_assignment_records_quiz_and_class(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        self.assertEqual(ctx["assignment"]["kind"], "quiz")
        self.assertEqual(ctx["assignment"]["source_id"], ctx["quiz"]["id"])
        listed = api.list_class_assignments(ctx["instructor"]["id"], ctx["class"]["id"])
        self.assertEqual(len(listed["assignments"]), 1)

    def test_only_owner_instructor_can_assign(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        # Make a second instructor on a separate notebook/quiz; they can't reuse the
        # first instructor's quiz because they don't own that notebook.
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            pass
        other = api.register_user("other@x.com", "password9")["user"]
        api.set_user_role(ctx["boss"]["id"], other["id"], "instructor")
        with self.assertRaises(PermissionError):
            api.create_assignment(
                instructor_id=other["id"],
                class_id=ctx["class"]["id"],
                kind="quiz",
                source_id=ctx["quiz"]["id"],
                title="Sneaky",
            )

    def test_student_submits_and_attempt_is_linked(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        answers = []  # empty answers; eval gracefully scores 0
        result = api.submit_assignment(ctx["student"]["id"], ctx["assignment"]["id"], answers)
        self.assertIn("attempt", result)
        self.assertEqual(result["submission"]["assignment_id"], ctx["assignment"]["id"])
        listed = api.list_assignment_submissions(ctx["instructor"]["id"], ctx["assignment"]["id"])
        self.assertEqual(len(listed["submissions"]), 1)
        self.assertEqual(listed["submissions"][0]["student_id"], ctx["student"]["id"])

    def test_non_enrolled_cannot_submit(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        stranger = api.register_user("nope@x.com", "password9")["user"]
        with self.assertRaises(PermissionError):
            api.submit_assignment(stranger["id"], ctx["assignment"]["id"], [])

    def test_student_my_assignments_shows_assignment(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        mine = api.list_assignments_for_student(ctx["student"]["id"])
        self.assertEqual(len(mine["assignments"]), 1)
        self.assertEqual(mine["assignments"][0]["class_name"], ctx["class"]["name"])


# ── Class analytics ─────────────────────────────────────────────────────────

class Phase8AnalyticsTests(unittest.TestCase):
    def test_analytics_reports_completion_and_avg(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        api.submit_assignment(ctx["student"]["id"], ctx["assignment"]["id"], [])
        analytics = api.class_analytics(ctx["instructor"]["id"], ctx["class"]["id"])
        self.assertEqual(analytics["enrolled_count"], 1)
        self.assertEqual(analytics["assignment_count"], 1)
        self.assertEqual(len(analytics["per_assignment"]), 1)
        row = analytics["per_assignment"][0]
        self.assertEqual(row["submitted_count"], 1)
        self.assertEqual(row["enrolled_count"], 1)
        self.assertEqual(row["completion_rate"], 100.0)

    def test_analytics_visible_only_to_class_instructor(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        with self.assertRaises(PermissionError):
            api.class_analytics(ctx["student"]["id"], ctx["class"]["id"])


# ── Persistence + cascade ──────────────────────────────────────────────────

class Phase8PersistenceTests(unittest.TestCase):
    def test_class_and_assignment_survive_reopen(self) -> None:
        path = str(Path(tempfile.mkdtemp()) / "p8.db")
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI(SqliteStudyLabStore(path))
            boss = api.register_user("boss@x.com", "password0")["user"]
            instructor = api.register_user("t@x.com", "password1")["user"]
            api.set_user_role(boss["id"], instructor["id"], "instructor")
            student = api.register_user("kid@x.com", "password2")["user"]
            nb = api.create_notebook("N", user_id=instructor["id"])
            api.upload_source(nb["id"], "Notes", SAMPLE)
            quiz = api.generate_quiz(nb["id"], num_questions=2)
            cls = api.create_class(instructor["id"], "C")
            api.enroll_in_class(student["id"], cls["code"])
            assignment = api.create_assignment(
                instructor_id=instructor["id"],
                class_id=cls["id"],
                kind="quiz",
                source_id=quiz["id"],
                title="HW",
            )
            api.submit_assignment(student["id"], assignment["id"], [])
            api.store.close()

            reopened = StudyLabAPI(SqliteStudyLabStore(path))
            mine = reopened.list_my_classes(instructor["id"])
            self.assertEqual(len(mine["teaching"]), 1)
            listed = reopened.list_class_assignments(instructor["id"], cls["id"])
            self.assertEqual(len(listed["assignments"]), 1)
            subs = reopened.list_assignment_submissions(instructor["id"], assignment["id"])
            self.assertEqual(len(subs["submissions"]), 1)
            reopened.store.close()

    def test_instructor_deletion_cascades_classes_and_submissions(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        api.submit_assignment(ctx["student"]["id"], ctx["assignment"]["id"], [])
        api.delete_account(ctx["instructor"]["id"])
        # Everything the instructor owned is gone.
        self.assertNotIn(ctx["class"]["id"], api.store.classes)
        self.assertNotIn(ctx["assignment"]["id"], api.store.assignments)
        self.assertEqual(api.store.submissions_for_student(ctx["student"]["id"]), [])

    def test_student_deletion_drops_their_enrollment_and_submissions(self) -> None:
        api = StudyLabAPI()
        ctx = _setup_class_with_quiz(api)
        api.submit_assignment(ctx["student"]["id"], ctx["assignment"]["id"], [])
        api.delete_account(ctx["student"]["id"])
        self.assertEqual(api.store.enrollments_for_user(ctx["student"]["id"]), [])
        self.assertEqual(api.store.submissions_for_student(ctx["student"]["id"]), [])
        # Class still exists for the instructor.
        self.assertIn(ctx["class"]["id"], api.store.classes)


if __name__ == "__main__":
    unittest.main()
