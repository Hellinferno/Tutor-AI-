from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import KnowledgeState, StudentProfile, TopicMastery
from .store import InMemoryStudyLabStore


class StudentModel:
    def __init__(self, store: InMemoryStudyLabStore) -> None:
        self.store = store

    def compute_mastery(
        self,
        user_id: str,
        notebook_id: str,
    ) -> KnowledgeState:
        self.store.require_notebook(notebook_id)

        profile = self.store.student_profile_for(user_id, notebook_id)
        if profile is None:
            profile = StudentProfile(
                id=self.store.next_id("sprofile"),
                user_id=user_id,
                notebook_id=notebook_id,
            )
            self.store.add_student_profile(profile)

        # Collect all eval reports for this user+notebook
        reports = [
            r for r in self.store.eval_reports.values()
            if r.attempt_id
            and self.store.attempts.get(r.attempt_id)
            and self.store.attempts[r.attempt_id].user_id == user_id
        ]

        topic_scores: dict[str, list[float]] = {}
        for report in reports:
            for topic in report.weak_topics:
                topic_scores.setdefault(topic, []).append(0.0)
            for topic in report.strong_topics:
                topic_scores.setdefault(topic, []).append(report.percentage / 100.0)

        masteries: list[TopicMastery] = []
        self.store.clear_topic_masteries(profile.id)
        for topic, scores in topic_scores.items():
            avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
            mastery = TopicMastery(
                id=self.store.next_id("tmastery"),
                student_profile_id=profile.id,
                topic=topic,
                score=avg_score,
                attempt_count=len(scores),
                last_attempt_date=reports[-1].attempt_id if reports else None,
            )
            self.store.add_topic_mastery(mastery)
            masteries.append(mastery)

        profile.updated_at = datetime.now(timezone.utc).isoformat()
        self.store.add_student_profile(profile)

        all_scores = [m.score for m in masteries]
        overall = round(sum(all_scores) / max(len(all_scores), 1), 2)
        weak = [m.topic for m in masteries if m.score < 0.6]
        strong = [m.topic for m in masteries if m.score >= 0.8]

        return KnowledgeState(
            user_id=user_id,
            notebook_id=notebook_id,
            masteries=masteries,
            overall_score=overall,
            weak_topics=weak,
            strong_topics=strong,
        )

    def get_knowledge_state(self, user_id: str, notebook_id: str) -> KnowledgeState | None:
        profile = self.store.student_profile_for(user_id, notebook_id)
        if profile is None:
            return None
        masteries = self.store.topic_masteries_for(profile.id)
        all_scores = [m.score for m in masteries]
        overall = round(sum(all_scores) / max(len(all_scores), 1), 2) if all_scores else 0.0
        return KnowledgeState(
            user_id=user_id,
            notebook_id=notebook_id,
            masteries=masteries,
            overall_score=overall,
            weak_topics=[m.topic for m in masteries if m.score < 0.6],
            strong_topics=[m.topic for m in masteries if m.score >= 0.8],
        )

    def weak_topics(self, user_id: str, notebook_id: str, threshold: float = 0.6) -> list[str]:
        state = self.get_knowledge_state(user_id, notebook_id)
        return state.weak_topics if state else []
