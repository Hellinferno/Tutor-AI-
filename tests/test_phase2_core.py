from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI  # noqa: E402
from studylab_core.models import QuizQuestion  # noqa: E402


SAMPLE = """
Gradient descent updates parameters by moving opposite the gradient of the loss function.
The update rule is theta := theta - eta * gradient. Feature scaling helps convergence.
Net present value discounts each cash flow by the required return.
"""


class Phase2TeachingTests(unittest.TestCase):
    def test_teaching_session_creates_concept_progression(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        session = api.start_teaching(notebook["id"])
        self.assertIn("id", session)
        self.assertIn("concepts", session)
        self.assertGreaterEqual(len(session["concepts"]), 1)
        self.assertEqual(session["current_concept_idx"], 0)

    def test_teaching_navigation_advances_and_returns(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Test")
        api.upload_source(notebook["id"], "Sample", SAMPLE)
        session = api.start_teaching(notebook["id"])
        sid = session["id"]
        if len(session["concepts"]) > 1:
            next_s = api.teaching_next(sid)
            self.assertGreaterEqual(next_s["current_concept_idx"], 1)
            prev_s = api.teaching_prev(sid)
            self.assertEqual(prev_s["current_concept_idx"], 0)

    def test_teaching_session_includes_citations(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        session = api.start_teaching(notebook["id"])
        for concept in session["concepts"]:
            self.assertIn("name", concept)
            self.assertIn("explanation", concept)
            self.assertIn("whiteboard", concept)
            self.assertGreaterEqual(len(concept["whiteboard"]), 1)
        cited = [concept for concept in session["concepts"] if concept["citations"]]
        self.assertGreaterEqual(len(cited), 1)
        self.assertIn("source_id", cited[0]["citations"][0])


class Phase2QuizTests(unittest.TestCase):
    def test_quiz_generates_mcq(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=3, question_types=["mcq"])
        self.assertIn("id", quiz)
        self.assertGreaterEqual(len(quiz["questions"]), 1)
        first = quiz["questions"][0]
        self.assertEqual(first["type"], "mcq")
        self.assertIn("options", first)

    def test_quiz_generates_true_false(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["true_false"])
        first = quiz["questions"][0]
        self.assertEqual(first["type"], "true_false")

    def test_quiz_generates_short_answer(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["short_answer"])
        first = quiz["questions"][0]
        self.assertEqual(first["type"], "short_answer")

    def test_quiz_hides_answers_by_default(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["true_false"])
        view = api.get_quiz(quiz["id"], include_answers=False)
        for q in view["questions"]:
            self.assertEqual(q["correct_answer"], "")

    def test_quiz_answer_key(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["true_false"])
        key = api.get_quiz_answer_key(quiz["id"])
        self.assertIn("id", key)
        self.assertTrue(key["verified"])
        self.assertGreaterEqual(len(key["answers"]), 1)
        self.assertTrue(all(answer["verified"] for answer in key["answers"]))

    def test_quiz_can_generate_from_topic_without_sources(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Topic Practice")
        quiz = api.generate_quiz(notebook["id"], num_questions=3, question_types=["mcq", "true_false"], topic="linear regression")
        self.assertEqual(quiz["topic"], "linear regression")
        self.assertEqual(len(quiz["questions"]), 3)
        key = api.get_quiz_answer_key(quiz["id"])
        self.assertTrue(key["verified"])


class Phase2PaperTests(unittest.TestCase):
    def test_paper_generates_with_sections(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        paper = api.generate_paper(notebook["id"], duration_minutes=45)
        self.assertIn("id", paper)
        self.assertGreaterEqual(len(paper["sections"]), 1)
        self.assertEqual(paper["duration_minutes"], 45)

    def test_paper_hides_answers_by_default(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        paper = api.generate_paper(notebook["id"])
        view = api.get_paper(paper["id"], include_answers=False)
        for section in view["sections"]:
            for q in section["questions"]:
                self.assertEqual(q["correct_answer"], "")

    def test_paper_answer_key(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        paper = api.generate_paper(notebook["id"])
        key = api.get_paper_answer_key(paper["id"])
        self.assertIn("id", key)
        self.assertTrue(key["verified"])
        self.assertGreaterEqual(len(key["answers"]), 1)
        self.assertTrue(all(answer["verified"] for answer in key["answers"]))

    def test_paper_can_generate_from_topic_without_sources(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Topic Paper")
        paper = api.generate_paper(
            notebook["id"],
            sections=[{"title": "Topic MCQ", "num_questions": 2, "type": "mcq"}],
            topic="net present value",
        )
        self.assertEqual(len(paper["sections"]), 1)
        key = api.get_paper_answer_key(paper["id"])
        self.assertTrue(key["verified"])


class Phase2EvalTests(unittest.TestCase):
    def test_quiz_attempt_scoring(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["true_false"])
        key = api.get_quiz_answer_key(quiz["id"])
        answers = [{"question_id": a["question_id"], "answer": a["correct_answer"]} for a in key["answers"]]
        attempt = api.submit_attempt(quiz["id"], "quiz", answers)
        self.assertGreater(attempt["total_score"], 0)
        self.assertGreater(attempt["max_score"], 0)

    def test_quiz_attempt_with_wrong_answers(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["true_false"])
        questions = quiz["questions"]
        wrong_answers = [{"question_id": q["id"], "answer": "Wrong"} for q in questions]
        attempt = api.submit_attempt(quiz["id"], "quiz", wrong_answers)
        total_correct = sum(1 for a in attempt["answers"] if a["correct"])
        self.assertEqual(total_correct, 0)

    def test_eval_report_generates(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        quiz = api.generate_quiz(notebook["id"], num_questions=2, question_types=["true_false"])
        answers = [{"question_id": q["id"], "answer": "True"} for q in quiz["questions"]]
        attempt = api.submit_attempt(quiz["id"], "quiz", answers)
        report = api.get_report(attempt["id"])
        self.assertIn("id", report)
        self.assertIn("percentage", report)
        self.assertIn("summary", report)

    def test_paper_attempt_scoring(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        paper = api.generate_paper(notebook["id"])
        key = api.get_paper_answer_key(paper["id"])
        answers = [{"question_id": a["question_id"], "answer": a["correct_answer"]} for a in key["answers"]]
        attempt = api.submit_attempt(paper["id"], "paper", answers)
        self.assertGreater(attempt["total_score"], 0)


class Phase2EdgeCaseTests(unittest.TestCase):
    def test_empty_notebook_raises_on_quiz(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Empty")
        with self.assertRaises(ValueError):
            api.generate_quiz(notebook["id"])

    def test_empty_notebook_raises_on_paper(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Empty")
        with self.assertRaises(ValueError):
            api.generate_paper(notebook["id"])

    def test_teaching_on_empty_notebook_creates_fallback(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Empty")
        session = api.start_teaching(notebook["id"])
        self.assertGreaterEqual(len(session["concepts"]), 1)


if __name__ == "__main__":
    unittest.main()
