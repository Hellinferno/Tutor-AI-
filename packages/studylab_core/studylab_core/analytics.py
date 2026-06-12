from __future__ import annotations

from typing import Any

from .store import InMemoryStudyLabStore


class AnalyticsEngine:
    def __init__(self, store: InMemoryStudyLabStore) -> None:
        self.store = store

    def notebook_trends(self, notebook_id: str) -> list[dict[str, Any]]:
        self.store.require_notebook(notebook_id)
        reports = [r for r in self.store.eval_reports.values()
                   if r.attempt_id
                   and self.store.attempts.get(r.attempt_id)
                   and self.store.attempts[r.attempt_id].source_id.startswith("quiz_")
                   and self.store.quizzes.get(self.store.attempts[r.attempt_id].source_id)
                   and self.store.quizzes[self.store.attempts[r.attempt_id].source_id].notebook_id == notebook_id]
        reports.sort(key=lambda r: r.attempt_id)
        return [
            {
                "attempt_id": r.attempt_id,
                "score": r.percentage,
                "max_score": r.max_score,
                "weak_topics": r.weak_topics,
                "strong_topics": r.strong_topics,
            }
            for r in reports
        ]

    def user_summary(self, user_id: str) -> dict[str, Any]:
        attempts = [a for a in self.store.attempts.values() if a.user_id == user_id]
        reports = [r for r in self.store.eval_reports.values()
                   if r.attempt_id and self.store.attempts.get(r.attempt_id)
                   and self.store.attempts[r.attempt_id].user_id == user_id]

        if not reports:
            return {
                "user_id": user_id,
                "total_attempts": 0,
                "avg_score": 0.0,
                "top_weak_topics": [],
                "top_strong_topics": [],
                "total_time_minutes": 0,
            }

        scores = [r.percentage for r in reports]
        weak_counts: dict[str, int] = {}
        strong_counts: dict[str, int] = {}
        for r in reports:
            for t in r.weak_topics:
                weak_counts[t] = weak_counts.get(t, 0) + 1
            for t in r.strong_topics:
                strong_counts[t] = strong_counts.get(t, 0) + 1

        sessions = self.store.user_sessions(user_id)
        total_minutes = 0
        for s in sessions:
            if s.ended_at:
                import datetime
                try:
                    start = datetime.datetime.fromisoformat(s.started_at)
                    end = datetime.datetime.fromisoformat(s.ended_at)
                    total_minutes += max(int((end - start).total_seconds() / 60), 1)
                except Exception:
                    total_minutes += 1

        return {
            "user_id": user_id,
            "total_attempts": len(attempts),
            "avg_score": round(sum(scores) / len(scores), 1),
            "top_weak_topics": sorted(weak_counts, key=weak_counts.get, reverse=True)[:5],
            "top_strong_topics": sorted(strong_counts, key=strong_counts.get, reverse=True)[:5],
            "total_time_minutes": total_minutes,
        }
