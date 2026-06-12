"use client";

import { useState } from "react";
import { ApiError, computeMastery, getNotebookTrends, getUserSummary } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { KnowledgeState, TrendPoint, UserSummary } from "../lib/types";

export function AnalyticsPanel() {
  const { notebookId, userId } = useNotebook();
  const [mastery, setMastery] = useState<KnowledgeState | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [summary, setSummary] = useState<UserSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!notebookId) return;
    setBusy(true);
    setError(null);
    try {
      const [m, t, s] = await Promise.all([
        computeMastery(userId, notebookId),
        getNotebookTrends(notebookId),
        getUserSummary(userId),
      ]);
      setMastery(m);
      setTrends(t.trends);
      setSummary(s);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load analytics.");
    } finally {
      setBusy(false);
    }
  }

  const overallPct = mastery ? Math.round(mastery.overall_score * 100) : null;

  return (
    <section className="panel wide" id="progress">
      <div className="panelHeader">
        <h3>Progress dashboard</h3>
        <span className="badge">Analytics</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and submit a quiz attempt first.</p>}

      <div className="analyticsGrid">
        <div className="analyticsCard">
          <p className="eyebrow">Overall mastery</p>
          <strong className="bigNumber">{overallPct === null ? "--" : `${overallPct}%`}</strong>
          <div className="topicsList">
            {mastery?.strong_topics.map((t) => (
              <span className="strongTag" key={`s-${t}`}>
                {t}
              </span>
            ))}
            {mastery?.weak_topics.map((t) => (
              <span className="weakTag" key={`w-${t}`}>
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="analyticsCard">
          <p className="eyebrow">Attempts</p>
          <strong className="bigNumber">{summary?.total_attempts ?? "--"}</strong>
          <small>avg score {summary ? `${summary.avg_score}%` : "--"}</small>
        </div>
        <div className="analyticsCard">
          <p className="eyebrow">Study time</p>
          <strong className="bigNumber">{summary ? `${summary.total_time_minutes}m` : "--"}</strong>
          <small>tracked sessions</small>
        </div>
      </div>

      <div className="trendChart">
        <p className="eyebrow">Score trend (per attempt)</p>
        {trends.length === 0 ? (
          <p className="muted13">No attempts yet — submit a quiz to populate the trend.</p>
        ) : (
          <div className="barChart">
            {trends.map((pt) => (
              <div className="barWrap" key={pt.attempt_id}>
                <div className="bar" style={{ height: `${Math.max(pt.score, 4)}%` }} />
                <small>{Math.round(pt.score)}%</small>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <small className="errorText">{error}</small>}
      <button type="button" onClick={refresh} disabled={busy || !notebookId}>
        {busy ? "…" : "Refresh analytics"}
      </button>
    </section>
  );
}
