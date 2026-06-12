"use client";

import { useState } from "react";
import { ApiError, generateRevisionCards, getDueCards, getRevisionStats, reviewCard } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { CardStats, RevisionCard } from "../lib/types";

export function RevisionPanel() {
  const { notebookId, userId } = useNotebook();
  const [due, setDue] = useState<RevisionCard[]>([]);
  const [stats, setStats] = useState<CardStats | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const [dueRes, statsRes] = await Promise.all([getDueCards(userId), getRevisionStats(userId)]);
      setDue(dueRes.cards);
      setStats(statsRes);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load revision data.");
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    if (!notebookId) return;
    setBusy(true);
    setError(null);
    try {
      await generateRevisionCards(notebookId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate cards.");
    } finally {
      setBusy(false);
    }
  }

  async function review(correct: boolean) {
    const card = due[0];
    if (!card) return;
    setBusy(true);
    setError(null);
    try {
      await reviewCard(card.id, correct);
      setDue((prev) => prev.slice(1));
      setStats(await getRevisionStats(userId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Review failed.");
    } finally {
      setBusy(false);
    }
  }

  const current = due[0];

  return (
    <section className="panel" id="revise">
      <div className="panelHeader">
        <h3>Spaced revision</h3>
        <span className="badge">SM-2</span>
      </div>

      <div className="revisionStats">
        <div className="statBox">
          <strong>{stats?.due ?? "--"}</strong>
          <small>due today</small>
        </div>
        <div className="statBox">
          <strong>{stats?.avg_easiness ?? "--"}</strong>
          <small>avg EF</small>
        </div>
        <div className="statBox">
          <strong>{stats?.lapsed ?? "--"}</strong>
          <small>lapsed</small>
        </div>
      </div>

      {current ? (
        <>
          <div className="revisionCardDemo">
            <p className="cardTopic">
              <strong>{current.topic}</strong>
            </p>
            <p className="cardQuestion">Recall what you know about &ldquo;{current.topic}&rdquo;.</p>
            <p className="cardHint">Interval {current.interval_days}d · streak {current.correct_streak}</p>
          </div>
          <div className="cardActions">
            <button type="button" className="forgotBtn" onClick={() => review(false)} disabled={busy}>
              Forgot
            </button>
            <button type="button" className="recallBtn" onClick={() => review(true)} disabled={busy}>
              Recalled
            </button>
          </div>
        </>
      ) : (
        <p className="cardHint">No cards due. Generate cards from your notebook, then review.</p>
      )}

      {error && <small className="errorText">{error}</small>}
      <div className="inlineForm">
        <button type="button" onClick={generate} disabled={busy || !notebookId}>
          Generate cards
        </button>
        <button type="button" className="secondary" onClick={refresh} disabled={busy}>
          Review due cards
        </button>
      </div>
    </section>
  );
}
