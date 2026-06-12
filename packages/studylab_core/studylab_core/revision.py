from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .models import RevisionCard
from .store import InMemoryStudyLabStore


class RepetitionEngine:
    def __init__(self, store: InMemoryStudyLabStore) -> None:
        self.store = store

    def generate_cards(
        self,
        notebook_id: str,
        user_id: str,
        topics: list[str] | None = None,
        source: str = "manual",
    ) -> list[RevisionCard]:
        self.store.require_notebook(notebook_id)
        if topics is None:
            guides = self.store.notebook_guides(notebook_id)
            topics = list({c for g in guides for c in g.key_concepts})

        if not topics:
            topics = ["review"]

        cards: list[RevisionCard] = []
        today = datetime.now(timezone.utc).date().isoformat()
        for topic in topics:
            card = RevisionCard(
                id=self.store.next_id("revcard"),
                user_id=user_id,
                notebook_id=notebook_id,
                topic=topic,
                due_date=today,
                interval_days=1,
                source=source,
            )
            self.store.add_revision_card(card)
            cards.append(card)
        return cards

    def due_cards(self, user_id: str) -> list[RevisionCard]:
        today = datetime.now(timezone.utc).date().isoformat()
        return self.store.due_revision_cards(user_id, today)

    def review_card(self, card_id: str, correct: bool) -> RevisionCard:
        card = self.store.require_revision_card(card_id)
        today = datetime.now(timezone.utc).date().isoformat()

        if correct:
            card.correct_streak += 1
            card.easiness_factor = min(card.easiness_factor + 0.1, 2.5)
            interval = max(int(card.easiness_factor * card.interval_days), 1) if card.interval_days > 1 else 1
            if card.correct_streak >= 2:
                interval = max(interval * 2, 3)
            card.interval_days = interval
            card.due_date = (datetime.now(timezone.utc) + timedelta(days=interval)).date().isoformat()
            card.state = "done"
        else:
            card.correct_streak = 0
            card.easiness_factor = max(card.easiness_factor - 0.2, 1.3)
            card.interval_days = 1
            card.due_date = today
            card.state = "lapsed"

        self.store.save_revision_card(card)
        return card

    def card_stats(self, user_id: str) -> dict[str, Any]:
        cards = [c for c in self.store.revision_cards.values() if c.user_id == user_id]
        today = datetime.now(timezone.utc).date().isoformat()
        return {
            "total": len(cards),
            "due": sum(1 for c in cards if c.due_date <= today),
            "done": sum(1 for c in cards if c.state == "done"),
            "lapsed": sum(1 for c in cards if c.state == "lapsed"),
            "avg_easiness": round(sum(c.easiness_factor for c in cards) / max(len(cards), 1), 2),
        }
