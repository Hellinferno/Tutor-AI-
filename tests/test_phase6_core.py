from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import (  # noqa: E402
    AuthError,
    RateLimitError,
    SqliteStudyLabStore,
    StudyLabAPI,
    make_rate_limiter_from_env,
)
from studylab_core.auth import make_auth_secret  # noqa: E402

SAMPLE = (
    "Gradient descent updates parameters by moving opposite the gradient of the loss. "
    "The update rule is theta := theta - eta * gradient."
)


class _EnvGuard:
    """Context manager to set/restore env vars cleanly inside a test."""

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


# ── Account self-service ───────────────────────────────────────────────────

class Phase6AccountTests(unittest.TestCase):
    def _user(self, api: StudyLabAPI):
        return api.register_user("dia@example.com", "gradient123")["user"]["id"]

    def test_change_password(self) -> None:
        api = StudyLabAPI()
        uid = self._user(api)
        api.change_password(uid, "gradient123", "newpass123")
        self.assertTrue(api.login("dia@example.com", "newpass123"))

    def test_change_password_wrong_current_rejected(self) -> None:
        api = StudyLabAPI()
        uid = self._user(api)
        with self.assertRaises(AuthError):
            api.change_password(uid, "wrong", "newpass123")

    def test_change_password_short_new_rejected(self) -> None:
        api = StudyLabAPI()
        uid = self._user(api)
        with self.assertRaises(AuthError):
            api.change_password(uid, "gradient123", "short")

    def test_update_profile(self) -> None:
        api = StudyLabAPI()
        uid = self._user(api)
        out = api.update_profile(uid, subject_domain="finance", prefs={"theme": "dark"})
        self.assertEqual(out["subject_domain"], "finance")
        self.assertEqual(out["prefs"], {"theme": "dark"})

    def test_password_reset_flow(self) -> None:
        api = StudyLabAPI()
        self._user(api)
        token = api.request_password_reset("dia@example.com")["reset_token"]
        self.assertIsNotNone(token)
        api.reset_password(token, "resetpass1")
        self.assertTrue(api.login("dia@example.com", "resetpass1"))

    def test_reset_token_cannot_be_used_as_session(self) -> None:
        api = StudyLabAPI()
        self._user(api)
        token = api.request_password_reset("dia@example.com")["reset_token"]
        with self.assertRaises(AuthError):
            api.current_user(token)  # purpose mismatch

    def test_request_reset_unknown_email_no_token(self) -> None:
        api = StudyLabAPI()
        out = api.request_password_reset("nobody@example.com")
        self.assertTrue(out["ok"])
        self.assertIsNone(out["reset_token"])

    def test_reset_token_not_returned_when_auth_enforced(self) -> None:
        # In an enforced (production-like) deployment the reset token must NOT be
        # returned in the response body — it would be emailed out-of-band.
        with _EnvGuard(STUDYLAB_REQUIRE_AUTH="true", STUDYLAB_JWT_SECRET="strong-secret-value"):
            api = StudyLabAPI()
            api.register_user("dia@example.com", "gradient123")
            out = api.request_password_reset("dia@example.com")
            self.assertTrue(out["ok"])
            self.assertIsNone(out["reset_token"])

    def test_malformed_token_raises_autherror_not_value_error(self) -> None:
        # A malformed bearer must surface as AuthError (→ 401), never an uncaught 500.
        api = StudyLabAPI()
        for bad in ("not-a-jwt", "aaa.bbb.c", "a.b.c", "", "x.y"):
            with self.assertRaises(AuthError):
                api.current_user(bad)

    def test_delete_account_removes_grading_artifacts(self) -> None:
        api = StudyLabAPI()
        uid = api.register_user("arun@example.com", "analytics1")["user"]["id"]
        nb = api.create_notebook("Mine", user_id=uid)
        api.upload_source(nb["id"], "GD", SAMPLE)
        quiz = api.generate_quiz(nb["id"], num_questions=2)
        api.get_quiz_answer_key(quiz["id"])  # creates an answer_key
        if quiz["questions"]:
            answers = [{"question_id": q["id"], "answer": q["correct_answer"]} for q in quiz["questions"]]
            attempt = api.submit_attempt(quiz["id"], "quiz", answers, user_id=uid)
            api.get_report(attempt["id"])  # creates an eval_report
        api.delete_account(uid)
        self.assertEqual([k for k in api.store.answer_keys.values() if k.source_id == quiz["id"]], [])
        self.assertEqual(list(api.store.eval_reports.values()), [])

    def test_delete_account_cascade(self) -> None:
        api = StudyLabAPI()
        uid = self._user(api)
        nb = api.create_notebook("Mine", user_id=uid)
        api.upload_source(nb["id"], "GD", SAMPLE)
        api.set_plan(uid, "pro")
        api.delete_account(uid)
        self.assertNotIn(uid, api.store.users)
        self.assertEqual([n for n in api.store.notebooks.values() if n.user_id == uid], [])
        self.assertEqual([s for s in api.store.sources.values() if s.notebook_id == nb["id"]], [])
        self.assertIsNone(api.store.subscription_for(uid))

    def test_delete_account_cascade_sqlite(self) -> None:
        path = str(Path(tempfile.mkdtemp()) / "p6.db")
        api = StudyLabAPI(SqliteStudyLabStore(path))
        uid = api.register_user("fiona@example.com", "valuation9")["user"]["id"]
        nb = api.create_notebook("Mine", user_id=uid)
        api.upload_source(nb["id"], "GD", SAMPLE)
        api.delete_account(uid)
        self.assertNotIn(uid, api.store.users)
        self.assertNotIn(nb["id"], api.store.notebooks)
        api.store.close()


# ── Input size caps ────────────────────────────────────────────────────────

class Phase6InputCapTests(unittest.TestCase):
    def test_upload_over_cap_rejected(self) -> None:
        with _EnvGuard(STUDYLAB_MAX_SOURCE_CHARS="50"):
            api = StudyLabAPI()
            nb = api.create_notebook("N")
            with self.assertRaises(ValueError):
                api.upload_source(nb["id"], "big", "x" * 100)

    def test_upload_under_cap_ok(self) -> None:
        with _EnvGuard(STUDYLAB_MAX_SOURCE_CHARS="100000"):
            api = StudyLabAPI()
            nb = api.create_notebook("N")
            out = api.upload_source(nb["id"], "ok", SAMPLE)
            self.assertIn("source", out)

    def test_connector_import_over_cap_rejected(self) -> None:
        with _EnvGuard(STUDYLAB_MAX_SOURCE_CHARS="50"):
            api = StudyLabAPI()
            nb = api.create_notebook("N")
            with self.assertRaises(ValueError):
                api.import_source(nb["id"], "website", "big", {"url": "https://e.com/a", "extracted_text": "x" * 100})


# ── Rate limiter ───────────────────────────────────────────────────────────

class Phase6RateLimitTests(unittest.TestCase):
    def test_allows_then_blocks(self) -> None:
        limiter = make_rate_limiter_from_env("2/60")
        limiter.check("ip1")
        limiter.check("ip1")
        with self.assertRaises(RateLimitError):
            limiter.check("ip1")

    def test_separate_keys_independent(self) -> None:
        limiter = make_rate_limiter_from_env("1/60")
        limiter.check("a")
        limiter.check("b")  # different key, allowed
        with self.assertRaises(RateLimitError):
            limiter.check("a")

    def test_empty_spec_disabled(self) -> None:
        self.assertIsNone(make_rate_limiter_from_env(""))
        self.assertIsNone(make_rate_limiter_from_env(None))

    def test_invalid_spec_raises(self) -> None:
        with self.assertRaises(ValueError):
            make_rate_limiter_from_env("not-a-spec")


# ── JWT secret hardening ───────────────────────────────────────────────────

class Phase6SecretGuardTests(unittest.TestCase):
    def test_enforced_without_secret_raises(self) -> None:
        with _EnvGuard(STUDYLAB_REQUIRE_AUTH="true"):
            os.environ.pop("STUDYLAB_JWT_SECRET", None)
            os.environ.pop("STUDYLAB_DEV_INSECURE", None)
            with self.assertRaises(RuntimeError):
                make_auth_secret()

    def test_enforced_with_secret_ok(self) -> None:
        with _EnvGuard(STUDYLAB_REQUIRE_AUTH="true", STUDYLAB_JWT_SECRET="a-strong-secret-value"):
            self.assertEqual(make_auth_secret(), "a-strong-secret-value")

    def test_dev_fallback_when_not_enforced(self) -> None:
        with _EnvGuard():
            os.environ.pop("STUDYLAB_JWT_SECRET", None)
            os.environ.pop("STUDYLAB_REQUIRE_AUTH", None)
            self.assertTrue(make_auth_secret())  # dev fallback allowed

    def test_dev_insecure_override(self) -> None:
        with _EnvGuard(STUDYLAB_REQUIRE_AUTH="true", STUDYLAB_DEV_INSECURE="1"):
            os.environ.pop("STUDYLAB_JWT_SECRET", None)
            self.assertTrue(make_auth_secret())  # explicit override allowed


if __name__ == "__main__":
    unittest.main()
