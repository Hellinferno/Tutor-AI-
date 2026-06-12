"use client";

import { useState } from "react";
import { ApiError, revealStep, solve } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { SolveResponse } from "../lib/types";

export function SolvePanel() {
  const { notebookId } = useNotebook();
  const [content, setContent] = useState("Calculate NPV at 10% for cash flows -100, 60, 60.");
  const [result, setResult] = useState<SolveResponse | null>(null);
  const [revealed, setRevealed] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!content.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await solve(content.trim(), notebookId ?? undefined);
      setResult(res);
      setRevealed(res.steps.filter((s) => s.revealed).map((s) => s.idx));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Solve failed.");
    } finally {
      setBusy(false);
    }
  }

  async function reveal() {
    if (!result) return;
    const next = result.steps.find((s) => !revealed.includes(s.idx));
    if (!next) return;
    try {
      await revealStep(result.solution_id, next.idx);
      setRevealed((prev) => [...prev, next.idx]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reveal failed.");
    }
  }

  const allRevealed = result ? revealed.length >= result.steps.length : false;

  return (
    <section className="panel" id="solve">
      <div className="panelHeader">
        <h3>Verified solve</h3>
        {result && <span className={result.verified ? "verified" : "badge"}>{result.verified ? "Verified" : "Unverified"}</span>}
      </div>

      <label className="inputRow">
        <span>Problem</span>
        <textarea value={content} onChange={(e) => setContent(e.target.value)} />
      </label>
      <button type="button" onClick={run} disabled={busy || !content.trim()}>
        {busy ? "Solving…" : "Solve & verify"}
      </button>
      {error && <small className="errorText">{error}</small>}

      {result && (
        <>
          <div className="solveResult">
            <span>Answer</span>
            <strong>{result.answer}</strong>
            <small>
              {result.verify_method}
              {result.from_cache ? " · from cache" : ""} · {result.latency_ms}ms
            </small>
          </div>
          <div className="spaced">
            {result.steps
              .filter((s) => revealed.includes(s.idx))
              .map((s) => (
                <p className="muted13" key={s.idx}>
                  {s.idx + 1}. {s.text}
                </p>
              ))}
          </div>
          {!allRevealed && (
            <button type="button" className="secondary" onClick={reveal}>
              Reveal next step
            </button>
          )}
        </>
      )}
    </section>
  );
}
