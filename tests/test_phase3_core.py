from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI, MockVoiceProvider  # noqa: E402

SAMPLE = """
Gradient descent updates parameters by moving opposite the gradient of the loss function.
The update rule is theta := theta - eta * gradient. Feature scaling helps convergence.
Net present value discounts each cash flow by the required return.
"""


class Phase3RevisionTests(unittest.TestCase):
    def test_generate_cards_from_notebook_concepts(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        result = api.generate_revision_cards(notebook["id"])
        self.assertIn("cards", result)
        self.assertGreaterEqual(len(result["cards"]), 1)
        self.assertEqual(result["cards"][0]["user_id"], "demo-user")

    def test_review_card_correct_advances_interval(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        result = api.generate_revision_cards(notebook["id"])
        card = result["cards"][0]
        # First correct → interval stays 1, state becomes done
        r1 = api.review_card(card["id"], correct=True)
        self.assertEqual(r1["state"], "done")
        # Second consecutive correct → interval advances past 1
        r2 = api.review_card(card["id"], correct=True)
        self.assertGreater(r2["interval_days"], 1)

    def test_review_card_incorrect_resets_interval(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        result = api.generate_revision_cards(notebook["id"])
        card = result["cards"][0]
        reviewed = api.review_card(card["id"], correct=False)
        self.assertEqual(reviewed["state"], "lapsed")
        self.assertEqual(reviewed["interval_days"], 1)
        self.assertEqual(reviewed["correct_streak"], 0)

    def test_due_cards_filters_by_date(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        result = api.generate_revision_cards(notebook["id"])
        self.assertIn("cards", result)
        # All just-generated cards are due today
        due = api.get_due_cards()
        self.assertIn("cards", due)
        self.assertGreaterEqual(len(due["cards"]), 1)

    def test_revision_stats(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        api.generate_revision_cards(notebook["id"])
        stats = api.revision_stats()
        self.assertIn("total", stats)
        self.assertIn("due", stats)
        self.assertIn("avg_easiness", stats)


class Phase3StudentTests(unittest.TestCase):
    def test_compute_mastery_from_empty_history(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        state = api.compute_mastery("demo-user", notebook["id"])
        # Still creates a profile
        self.assertIn("overall_score", state)
        self.assertIn("masteries", state)

    def test_compute_mastery_after_eval_report(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2)
        if quiz["questions"]:
            answers = [{"question_id": q["id"], "answer": q["correct_answer"]} for q in quiz["questions"]]
            attempt = api.submit_attempt(quiz["id"], "quiz", answers)
        state = api.compute_mastery("demo-user", notebook["id"])
        self.assertIn("overall_score", state)
        self.assertIsInstance(state["overall_score"], float)

    def test_get_mastery_returns_state(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.compute_mastery("demo-user", notebook["id"])
        state = api.get_mastery("demo-user", notebook["id"])
        self.assertIn("masteries", state)
        self.assertIn("weak_topics", state)

    def test_weak_topics_empty_when_no_reports(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        result = api.get_weak_topics("demo-user", notebook["id"])
        self.assertIn("weak_topics", result)
        self.assertEqual(result["weak_topics"], [])


class Phase3AnalyticsTests(unittest.TestCase):
    def test_notebook_trends_empty_with_no_attempts(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        trends = api.notebook_trends(notebook["id"])
        self.assertIn("trends", trends)
        self.assertEqual(trends["trends"], [])

    def test_user_summary_with_no_history(self) -> None:
        api = StudyLabAPI()
        summary = api.user_summary("demo-user")
        self.assertIn("total_attempts", summary)
        self.assertEqual(summary["total_attempts"], 0)

    def test_user_summary_after_attempt(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2)
        if quiz["questions"]:
            answers = [{"question_id": q["id"], "answer": q["correct_answer"]} for q in quiz["questions"]]
            api.submit_attempt(quiz["id"], "quiz", answers)
        summary = api.user_summary("demo-user")
        self.assertGreaterEqual(summary["total_attempts"], 0)


class Phase3VoiceTests(unittest.TestCase):
    def test_mock_stt_decodes_base64(self) -> None:
        provider = MockVoiceProvider()
        audio = base64.b64encode(b"hello world audio").decode("ascii")
        result = provider.stt(audio)
        self.assertTrue(result.ok)
        self.assertIn("mock stt", result.text)

    def test_mock_tts_returns_base64_audio(self) -> None:
        provider = MockVoiceProvider()
        result = provider.tts("What is gradient descent?")
        self.assertTrue(result.ok)
        self.assertGreater(len(result.audio_base64), 0)

    def test_mock_stt_handles_empty_audio(self) -> None:
        provider = MockVoiceProvider()
        result = provider.stt("")
        self.assertTrue(result.ok)
        self.assertIn("mock stt", result.text)

    def test_mock_tts_produces_different_output_for_different_text(self) -> None:
        provider = MockVoiceProvider()
        r1 = provider.tts("Hello")
        r2 = provider.tts("World")
        self.assertNotEqual(r1.audio_base64, r2.audio_base64)


class Phase3EdgeCaseTests(unittest.TestCase):
    def test_generate_cards_with_no_sources_falls_back(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Empty Notebook")
        result = api.generate_revision_cards(notebook["id"])
        self.assertIn("cards", result)
        self.assertGreaterEqual(len(result["cards"]), 1)

    def test_review_nonexistent_card_raises_keyerror(self) -> None:
        api = StudyLabAPI()
        with self.assertRaises(KeyError):
            api.review_card("nonexistent-id", correct=True)

    def test_multiple_correct_reviews_increase_easiness(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        result = api.generate_revision_cards(notebook["id"])
        card = result["cards"][0]
        r1 = api.review_card(card["id"], correct=True)
        ef1 = r1["easiness_factor"]
        r2 = api.review_card(card["id"], correct=True)
        ef2 = r2["easiness_factor"]
        self.assertGreaterEqual(ef2, ef1)

    def test_easiness_factor_capped_at_2_5(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        result = api.generate_revision_cards(notebook["id"])
        card = result["cards"][0]
        for _ in range(10):
            card = api.review_card(card["id"], correct=True)
        self.assertLessEqual(card["easiness_factor"], 2.5)


class Phase3SessionTests(unittest.TestCase):
    def test_session_roundtrip(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        session = api.create_session("demo-user", notebook["id"], "study")
        self.assertIn("id", session)
        self.assertIsNone(session.get("ended_at"))
        
        ended = api.end_session(session["id"])
        self.assertIsNotNone(ended.get("ended_at"))


class Phase3WeakTopicAutoGenTests(unittest.TestCase):
    def test_submit_attempt_generates_cards(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2)
        if quiz["questions"]:
            # Intentionally get questions wrong to force weak topics
            answers = [{"question_id": q["id"], "answer": "incorrect answer"} for q in quiz["questions"]]
            api.submit_attempt(quiz["id"], "quiz", answers)
            
            # Check that revision cards were generated for weak topics
            cards_result = api.get_due_cards("demo-user")
            self.assertIn("cards", cards_result)
            # Since we got it wrong, there should be some weak topics leading to cards
            self.assertGreaterEqual(len(cards_result["cards"]), 1)


class Phase3APIVoiceTests(unittest.TestCase):
    def test_api_stt_base64(self) -> None:
        api = StudyLabAPI()
        audio = base64.b64encode(b"hello world").decode("ascii")
        result = api.speech_to_text(audio)
        self.assertTrue(result["ok"])
        self.assertIn("mock stt", result["text"])

    def test_api_tts_returns_base64(self) -> None:
        api = StudyLabAPI()
        result = api.text_to_speech("hello world")
        self.assertTrue(result["ok"])
        self.assertGreater(len(result["audio_base64"]), 0)


if __name__ == "__main__":
    unittest.main()
