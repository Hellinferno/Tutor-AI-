from __future__ import annotations

import re

from .models import Attempt, AttemptSourceType, EvalReport
from .store import InMemoryStudyLabStore


class EvalEngine:
    def __init__(self, store: InMemoryStudyLabStore) -> None:
        self.store = store

    def evaluate_attempt(
        self,
        source_id: str,
        source_type: AttemptSourceType,
        user_answers: list[dict],
        user_id: str = "demo-user",
    ) -> Attempt:
        if source_type == "quiz":
            source = self.store.require_quiz(source_id)
            correct_map = {q.id: q for q in source.questions}
        elif source_type == "paper":
            source = self.store.require_question_paper(source_id)
            correct_map = {}
            for section in source.sections:
                for q in section.questions:
                    correct_map[q.id] = q
        else:
            raise ValueError(f"Unknown source_type: {source_type}")

        scored_answers: list[dict] = []
        total_score = 0.0
        max_score = 0.0

        for user_answer in user_answers:
            qid = user_answer.get("question_id", "")
            given = user_answer.get("answer", "")
            question = correct_map.get(qid)
            if not question:
                scored_answers.append({
                    "question_id": qid,
                    "given_answer": given,
                    "correct": False,
                    "score": 0,
                    "max_score": 0,
                    "feedback": "Question not found.",
                })
                continue

            correct = self._check_answer(given, question.correct_answer, question.type)
            points = question.points if correct else 0
            total_score += points
            max_score += question.points
            scored_answers.append({
                "question_id": qid,
                "given_answer": given,
                "correct": correct,
                "score": points,
                "max_score": question.points,
                "feedback": "Correct!" if correct else f"Incorrect. Expected: {question.correct_answer[:100]}",
            })

        attempt = Attempt(
            id=self.store.next_id("attempt"),
            source_id=source_id,
            source_type=source_type,
            user_id=user_id,
            answers=scored_answers,
            total_score=total_score,
            max_score=max_score,
        )
        return self.store.add_attempt(attempt)

    def generate_report(self, attempt_id: str) -> EvalReport:
        attempt = self.store.require_attempt(attempt_id)
        per_question = attempt.answers
        correct_qs = [a for a in per_question if a.get("correct")]
        incorrect_qs = [a for a in per_question if not a.get("correct")]

        percentage = round((attempt.total_score / max(attempt.max_score, 1)) * 100, 1)
        weak_topics = [f"Question {a['question_id'][:8]}" for a in incorrect_qs[:5]]
        strong_topics = [f"Question {a['question_id'][:8]}" for a in correct_qs[:5]]

        summary = self._build_summary(percentage, len(correct_qs), len(incorrect_qs))

        report = EvalReport(
            id=self.store.next_id("report"),
            attempt_id=attempt_id,
            total_score=attempt.total_score,
            max_score=attempt.max_score,
            percentage=percentage,
            per_question=per_question,
            weak_topics=weak_topics,
            strong_topics=strong_topics,
            summary=summary,
        )
        return self.store.add_eval_report(report)

    def _check_answer(self, given: str, expected: str, q_type: str) -> bool:
        if q_type == "true_false":
            return given.strip().lower() == expected.strip().lower()

        if q_type == "mcq":
            return given.strip().lower() == expected.strip().lower()

        given_clean = re.sub(r"\s+", " ", given.strip().lower())
        expected_clean = re.sub(r"\s+", " ", expected.strip().lower())

        if given_clean == expected_clean:
            return True
        try:
            given_num = float(given_clean)
            expected_num = float(expected_clean)
            return abs(given_num - expected_num) < 0.01
        except ValueError:
            pass
        given_tokens = set(given_clean.split())
        expected_tokens = set(expected_clean.split())
        if len(expected_tokens) > 2:
            overlap = len(given_tokens & expected_tokens) / len(expected_tokens)
            return overlap >= 0.6
        return False

    def _build_summary(self, percentage: float, correct: int, incorrect: int) -> str:
        total = correct + incorrect
        if percentage >= 80:
            level = "Excellent"
        elif percentage >= 60:
            level = "Good"
        elif percentage >= 40:
            level = "Fair"
        else:
            level = "Needs improvement"
        return f"{level}: {correct}/{total} correct ({percentage}%). Review the questions you missed to strengthen your understanding."
