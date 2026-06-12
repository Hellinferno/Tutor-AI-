"use client";

import { useState } from "react";
import { ApiError, getReport } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { EvalReport } from "../lib/types";

export function ReportPanel() {
  const { lastAttemptId } = useNotebook();
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!lastAttemptId) return;
    setBusy(true);
    setError(null);
    try {
      setReport(await getReport(lastAttemptId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="reports">
      <div className="panelHeader">
        <h3>Evaluation report</h3>
        <span className="badge">Performance</span>
      </div>

      <div className="reportSummary">
        <div className="scoreCircle">
          <strong>{report ? `${report.percentage}%` : "--"}</strong>
          <small>{report ? `${report.total_score}/${report.max_score}` : "/ --"}</small>
        </div>
        <p className="reportLevel">
          {report ? report.summary : "Submit a quiz or paper attempt, then load the evaluation."}
        </p>
      </div>

      <div className="reportBreakdown">
        <p className="eyebrow">Topic breakdown</p>
        <div className="topicRow">
          <span>Strong areas</span>
          <span className="strongTag">{report?.strong_topics.length ? report.strong_topics.join(", ") : "--"}</span>
        </div>
        <div className="topicRow">
          <span>Weak areas</span>
          <span className="weakTag">{report?.weak_topics.length ? report.weak_topics.join(", ") : "--"}</span>
        </div>
      </div>

      {error && <small className="errorText">{error}</small>}
      <button type="button" onClick={load} disabled={busy || !lastAttemptId}>
        {!lastAttemptId ? "No attempt yet" : busy ? "Loading…" : "View latest report"}
      </button>
    </section>
  );
}
