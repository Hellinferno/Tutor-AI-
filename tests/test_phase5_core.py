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
    QuotaExceededError,
    SqliteStudyLabStore,
    StudyLabAPI,
    hash_password,
    verify_password,
)

SAMPLE = (
    "Gradient descent updates parameters by moving opposite the gradient of the loss. "
    "The update rule is theta := theta - eta * gradient."
)


# ── Phase 5: Password hashing ──────────────────────────────────────────────

class Phase5PasswordTests(unittest.TestCase):
    def test_hash_is_salted_and_verifies(self) -> None:
        h1 = hash_password("gradient123")
        h2 = hash_password("gradient123")
        self.assertNotEqual(h1, h2)  # random salt → different hashes
        self.assertTrue(verify_password("gradient123", h1))
        self.assertTrue(verify_password("gradient123", h2))

    def test_wrong_password_fails(self) -> None:
        self.assertFalse(verify_password("wrong", hash_password("gradient123")))

    def test_hash_format_has_no_plaintext(self) -> None:
        h = hash_password("supersecretpw")
        self.assertIn("pbkdf2_sha256$", h)
        self.assertNotIn("supersecretpw", h)


# ── Phase 5: Auth (register / login / JWT) ─────────────────────────────────

class Phase5AuthTests(unittest.TestCase):
    def test_register_returns_token_and_public_user(self) -> None:
        api = StudyLabAPI()
        result = api.register_user("Dia@Example.com", "gradient123")
        self.assertEqual(result["user"]["email"], "dia@example.com")  # normalized
        self.assertNotIn("password_hash", result["user"])  # never leaked
        self.assertTrue(result["token"])

    def test_login_roundtrip_and_token_resolves_user(self) -> None:
        api = StudyLabAPI()
        api.register_user("dia@example.com", "gradient123")
        login = api.login("dia@example.com", "gradient123")
        me = api.current_user(login["token"])
        self.assertEqual(me["email"], "dia@example.com")

    def test_login_wrong_password_rejected(self) -> None:
        api = StudyLabAPI()
        api.register_user("dia@example.com", "gradient123")
        with self.assertRaises(AuthError):
            api.login("dia@example.com", "nope-wrong")

    def test_duplicate_email_rejected(self) -> None:
        api = StudyLabAPI()
        api.register_user("dia@example.com", "gradient123")
        with self.assertRaises(AuthError):
            api.register_user("dia@example.com", "another123")

    def test_short_password_rejected(self) -> None:
        api = StudyLabAPI()
        with self.assertRaises(AuthError):
            api.register_user("x@y.com", "short")

    def test_invalid_email_rejected(self) -> None:
        api = StudyLabAPI()
        with self.assertRaises(AuthError):
            api.register_user("not-an-email", "gradient123")

    def test_tampered_token_rejected(self) -> None:
        api = StudyLabAPI()
        token = api.register_user("dia@example.com", "gradient123")["token"]
        with self.assertRaises(AuthError):
            api.current_user(token[:-3] + "zzz")

    def test_garbage_token_rejected(self) -> None:
        api = StudyLabAPI()
        with self.assertRaises(AuthError):
            api.current_user("not.a.jwt")

    def test_user_survives_sqlite_reopen(self) -> None:
        path = str(Path(tempfile.mkdtemp()) / "auth.db")
        api = StudyLabAPI(SqliteStudyLabStore(path))
        uid = api.register_user("fiona@example.com", "valuation99")["user"]["id"]
        api.store.close()
        reopened = StudyLabAPI(SqliteStudyLabStore(path))
        login = reopened.login("fiona@example.com", "valuation99")
        self.assertEqual(login["user"]["id"], uid)
        reopened.store.close()


# ── Phase 5: Authorization (ownership) ─────────────────────────────────────

class Phase5AuthzTests(unittest.TestCase):
    def test_owner_can_access_notebook(self) -> None:
        api = StudyLabAPI()
        uid = api.register_user("dia@example.com", "gradient123")["user"]["id"]
        nb = api.create_notebook("Mine", user_id=uid)
        self.assertTrue(api.authorize_notebook(uid, nb["id"]))

    def test_non_owner_denied(self) -> None:
        api = StudyLabAPI()
        uid = api.register_user("dia@example.com", "gradient123")["user"]["id"]
        nb = api.create_notebook("Mine", user_id=uid)
        with self.assertRaises(PermissionError):
            api.authorize_notebook("intruder", nb["id"])


# ── Phase 5: Quota enforcement ─────────────────────────────────────────────

class Phase5QuotaTests(unittest.TestCase):
    def test_enforce_blocks_over_quota(self) -> None:
        api = StudyLabAPI()
        # Free tier paper quota is 5.
        for _ in range(5):
            api.pricing.enforce("u1", "paper")
        with self.assertRaises(QuotaExceededError):
            api.pricing.enforce("u1", "paper")

    def test_enforce_quota_api_returns_detail(self) -> None:
        api = StudyLabAPI()
        out = api.enforce_quota("u1", "quiz")
        self.assertEqual(out["quota"]["used"], 1)
        self.assertTrue(out["quota"]["allowed"])

    def test_pro_tier_never_blocks(self) -> None:
        api = StudyLabAPI()
        api.set_plan("u1", "pro")
        for _ in range(30):
            api.pricing.enforce("u1", "ask")  # unlimited → never raises

    def test_guard_enforces_when_env_set(self) -> None:
        api = StudyLabAPI()
        nb = api.create_notebook("N")
        os.environ["STUDYLAB_ENFORCE_QUOTAS"] = "true"
        try:
            ok = 0
            with self.assertRaises(QuotaExceededError):
                for i in range(7):
                    api.import_source(nb["id"], "website", f"A{i}", {"url": f"https://e.com/{i}", "extracted_text": SAMPLE})
                    ok += 1
            self.assertEqual(ok, 5)  # free source_import quota
        finally:
            del os.environ["STUDYLAB_ENFORCE_QUOTAS"]


# ── Phase 5: Observability metrics ─────────────────────────────────────────

class Phase5MetricsTests(unittest.TestCase):
    def test_metrics_track_ask_solve(self) -> None:
        api = StudyLabAPI()
        nb = api.create_notebook("ML")
        api.upload_source(nb["id"], "GD", SAMPLE)
        api.ask_notebook(nb["id"], "how does gradient descent update parameters?")  # grounded
        api.ask_notebook(nb["id"], "what is the capital of france?")  # refusal
        api.solve("What is 2 + 2 * 3?", subject="analytics")
        snap = api.metrics_snapshot()
        self.assertEqual(snap["asks"], 2)
        self.assertEqual(snap["solves"], 1)
        self.assertEqual(snap["weak_retrieval_refusal_rate"], 0.5)
        self.assertEqual(snap["verified_rate"], 1.0)
        self.assertEqual(snap["false_verified_rate"], 0.0)

    def test_metrics_snapshot_shape(self) -> None:
        api = StudyLabAPI()
        snap = api.metrics_snapshot()
        for key in (
            "asks", "weak_retrieval_refusal_rate", "citation_coverage_rate", "solves",
            "verified_rate", "false_verified_rate", "cache_hit_rate", "solve_latency_ms",
            "notion_export_success_rate",
        ):
            self.assertIn(key, snap)
        self.assertIn("p90", snap["solve_latency_ms"])


if __name__ == "__main__":
    unittest.main()
