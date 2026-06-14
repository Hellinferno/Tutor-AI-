from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI, SqliteStudyLabStore  # noqa: E402

SAMPLE = (
    "Gradient descent updates parameters by moving opposite the gradient of the loss function. "
    "The update rule is theta := theta - eta * gradient. Feature scaling helps convergence. "
    "Net present value discounts each future cash flow by the required rate of return."
)


def _seed(api: StudyLabAPI):
    notebook = api.create_notebook("ML Notes")
    api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
    return notebook


# ── Phase 4: Source connectors ────────────────────────────────────────────

class Phase4ConnectorTests(unittest.TestCase):
    def test_website_import_creates_cited_source(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Connectors")
        result = api.import_source(
            notebook["id"], "website", "GD article",
            {"url": "https://example.com/gd", "extracted_text": SAMPLE},
        )
        self.assertEqual(result["import"]["status"], "ready")
        self.assertEqual(result["import"]["connector_type"], "website")
        self.assertEqual(result["import"]["metadata"]["url"], "https://example.com/gd")
        self.assertGreaterEqual(len(result["source_guide"]["key_concepts"]), 1)
        # Imported content is queryable like any uploaded source.
        answer = api.ask_notebook(notebook["id"], "How does gradient descent update parameters?")
        self.assertEqual(answer["grounding"], "from_sources")

    def test_youtube_transcript_list_is_joined(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("YT")
        result = api.import_source(
            notebook["id"], "youtube", "Lecture",
            {"video_id": "abc123", "transcript": [{"text": "Gradient descent"}, {"text": "moves opposite the gradient."}]},
        )
        self.assertEqual(result["import"]["metadata"]["video_id"], "abc123")
        self.assertEqual(result["import"]["connector_type"], "youtube")

    def test_html_payload_is_stripped(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("HTML")
        html = "<html><head><style>.x{color:red}</style><script>evil()</script></head><body><p>Gradient descent moves opposite the gradient of the loss.</p></body></html>"
        result = api.import_source(
            notebook["id"], "website", "Stripped",
            {"url": "https://example.com/x", "html": html},
        )
        source = api.get_source(result["source"]["id"])["source"]
        self.assertNotIn("evil()", source["text"])
        self.assertNotIn("color:red", source["text"])
        self.assertIn("Gradient descent", source["text"])

    def test_google_doc_and_slides(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("GDocs")
        doc = api.import_source(notebook["id"], "google_doc", "Doc", {"document_id": "d1", "exported_text": SAMPLE})
        slides = api.import_source(notebook["id"], "google_slides", "Deck", {"presentation_id": "p1", "exported_text": SAMPLE})
        self.assertEqual(doc["import"]["connector_type"], "google_doc")
        self.assertEqual(slides["import"]["connector_type"], "google_slides")

    def test_unsupported_connector_rejected(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Bad")
        with self.assertRaises(ValueError):
            api.import_source(notebook["id"], "telepathy", "X", {"text": SAMPLE})  # type: ignore[arg-type]

    def test_missing_text_rejected(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Empty")
        with self.assertRaises(ValueError):
            api.import_source(notebook["id"], "website", "X", {"url": "https://e.com/a"})

    def test_website_requires_url(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("NoUrl")
        with self.assertRaises(ValueError):
            api.import_source(notebook["id"], "website", "X", {"extracted_text": SAMPLE})

    def test_invalid_url_rejected(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("BadUrl")
        with self.assertRaises(ValueError):
            api.import_source(notebook["id"], "website", "X", {"url": "not-a-url", "extracted_text": SAMPLE})

    def test_list_imports_scoped_to_notebook(self) -> None:
        api = StudyLabAPI()
        a = api.create_notebook("A")
        b = api.create_notebook("B")
        api.import_source(a["id"], "website", "A1", {"url": "https://e.com/a", "extracted_text": SAMPLE})
        listed = api.list_source_imports(a["id"])
        self.assertEqual(len(listed["imports"]), 1)
        self.assertEqual(len(api.list_source_imports(b["id"])["imports"]), 0)
        self.assertIn("website", listed["supported_types"])

    def test_import_meters_usage(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Meter")
        api.import_source(notebook["id"], "website", "A1", {"url": "https://e.com/a", "extracted_text": SAMPLE})
        quota = api.check_quota("demo-user", "source_import")
        self.assertEqual(quota["used"], 1)


# ── Phase 4: Multi-agent teaching ─────────────────────────────────────────

class Phase4MultiAgentTests(unittest.TestCase):
    def test_start_session_builds_agent_turns(self) -> None:
        api = StudyLabAPI()
        notebook = _seed(api)
        session = api.start_multi_agent_teaching(notebook["id"])
        self.assertGreaterEqual(len(session["concepts"]), 1)
        # 3 agent roles per concept.
        self.assertEqual(len(session["agent_turns"]), len(session["concepts"]) * 3)
        roles = {t["role"] for t in session["agent_turns"]}
        self.assertEqual(roles, {"concept_explainer", "grounding_verifier", "practice_coach"})

    def test_navigation_and_completion(self) -> None:
        api = StudyLabAPI()
        notebook = _seed(api)
        session = api.start_multi_agent_teaching(notebook["id"])
        n = len(session["concepts"])
        current = session
        for _ in range(n + 2):
            current = api.multi_agent_next(current["id"])
        self.assertTrue(current["completed"])
        self.assertEqual(current["current_concept_idx"], n - 1)
        back = api.multi_agent_prev(current["id"])
        self.assertFalse(back["completed"])

    def test_get_session_roundtrip(self) -> None:
        api = StudyLabAPI()
        notebook = _seed(api)
        session = api.start_multi_agent_teaching(notebook["id"])
        fetched = api.get_multi_agent_session(session["id"])
        self.assertEqual(fetched["id"], session["id"])

    def test_verifier_confidence_reflects_grounding(self) -> None:
        api = StudyLabAPI()
        notebook = _seed(api)
        session = api.start_multi_agent_teaching(notebook["id"])
        verifiers = [t for t in session["agent_turns"] if t["role"] == "grounding_verifier"]
        self.assertTrue(all(0.0 <= t["confidence"] <= 1.0 for t in verifiers))


# ── Phase 4: Pricing & economics ──────────────────────────────────────────

class Phase4PricingTests(unittest.TestCase):
    def test_list_plans(self) -> None:
        api = StudyLabAPI()
        plans = api.list_plans()["plans"]
        self.assertEqual([p["tier"] for p in plans], ["free", "scholar", "pro"])
        self.assertEqual(plans[0]["price_cents"], 0)
        self.assertGreater(plans[1]["price_cents"], 0)

    def test_default_subscription_is_free(self) -> None:
        api = StudyLabAPI()
        sub = api.get_subscription("u1")
        self.assertEqual(sub["tier"], "free")
        self.assertEqual(sub["status"], "active")

    def test_set_plan_changes_tier(self) -> None:
        api = StudyLabAPI()
        result = api.set_plan("u1", "scholar")
        self.assertEqual(result["subscription"]["tier"], "scholar")
        self.assertEqual(api.get_subscription("u1")["tier"], "scholar")

    def test_unknown_tier_rejected(self) -> None:
        api = StudyLabAPI()
        with self.assertRaises(ValueError):
            api.set_plan("u1", "platinum")  # type: ignore[arg-type]

    def test_metering_and_quota(self) -> None:
        api = StudyLabAPI()
        for _ in range(3):
            api.record_usage("u1", "quiz")
        quota = api.check_quota("u1", "quiz")
        self.assertEqual(quota["used"], 3)
        self.assertEqual(quota["limit"], 10)  # free tier quiz quota
        self.assertEqual(quota["remaining"], 7)
        self.assertTrue(quota["allowed"])

    def test_quota_blocks_when_exhausted(self) -> None:
        api = StudyLabAPI()
        for _ in range(5):
            api.record_usage("u1", "paper")  # free tier paper quota is 5
        quota = api.check_quota("u1", "paper")
        self.assertEqual(quota["remaining"], 0)
        self.assertFalse(quota["allowed"])

    def test_pro_tier_is_unlimited(self) -> None:
        api = StudyLabAPI()
        api.set_plan("u1", "pro")
        for _ in range(50):
            api.record_usage("u1", "ask")
        quota = api.check_quota("u1", "ask")
        self.assertIsNone(quota["limit"])
        self.assertTrue(quota["allowed"])

    def test_usage_summary_shape(self) -> None:
        api = StudyLabAPI()
        api.record_usage("u1", "ask")
        summary = api.usage_summary("u1")
        self.assertEqual(summary["tier"], "free")
        self.assertEqual(len(summary["actions"]), 7)
        ask = next(a for a in summary["actions"] if a["action"] == "ask")
        self.assertEqual(ask["used"], 1)


# ── Phase 4: SQLite persistence ───────────────────────────────────────────

class Phase4PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = str(Path(tempfile.mkdtemp()) / "p4.db")

    def test_phase4_state_survives_reopen(self) -> None:
        api = StudyLabAPI(SqliteStudyLabStore(self.path))
        notebook = api.create_notebook("ML")
        api.upload_source(notebook["id"], "GD", SAMPLE)
        imp = api.import_source(notebook["id"], "website", "A", {"url": "https://e.com/a", "extracted_text": SAMPLE})
        session = api.start_multi_agent_teaching(notebook["id"])
        api.set_plan("demo-user", "pro")
        api.record_usage("demo-user", "solve", 2)
        api.store.close()

        reopened = StudyLabAPI(SqliteStudyLabStore(self.path))
        self.assertEqual(len(reopened.list_source_imports(notebook["id"])["imports"]), 1)
        self.assertEqual(reopened.get_multi_agent_session(session["id"])["id"], session["id"])
        self.assertEqual(reopened.get_subscription("demo-user")["tier"], "pro")
        self.assertEqual(reopened.check_quota("demo-user", "solve")["used"], 2)
        # Connector-imported content is still retrievable after restart.
        self.assertIn(imp["import"]["id"], reopened.store.source_imports)
        reopened.store.close()


if __name__ == "__main__":
    unittest.main()
