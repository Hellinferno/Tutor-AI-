"use client";

import { useState } from "react";
import { ApiError, startTeaching, teachingNext, teachingPrev } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { WhiteboardSession } from "../lib/types";

export function TeachingPanel() {
  const { notebookId } = useNotebook();
  const [session, setSession] = useState<WhiteboardSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<WhiteboardSession>) {
    setBusy(true);
    setError(null);
    try {
      setSession(await fn());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Teaching action failed.");
    } finally {
      setBusy(false);
    }
  }

  const concept = session?.concepts[session.current_concept_idx];

  return (
    <section className="panel wide" id="teach">
      <div className="panelHeader">
        <h3>Teaching whiteboard</h3>
        <span className="badge">Concept walk-through</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and upload a source first.</p>}

      {session && concept && (
        <div className="conceptDisplay">
          <div className="conceptNav">
            <button type="button" onClick={() => run(() => teachingPrev(session.id))} disabled={busy || session.current_concept_idx === 0}>
              ← Previous
            </button>
            <span className="conceptCounter">
              {session.current_concept_idx + 1} / {session.concepts.length}
            </span>
            <button
              type="button"
              onClick={() => run(() => teachingNext(session.id))}
              disabled={busy || session.current_concept_idx >= session.concepts.length - 1}
            >
              Next →
            </button>
          </div>
          <div className="conceptContent">
            <strong className="conceptName">{concept.name}</strong>
            <p className="conceptExplanation">{concept.explanation}</p>
            {concept.whiteboard.map((el, i) => (
              <p className="muted13" key={i}>
                {el.katex ?? el.text ?? el.type}
              </p>
            ))}
            {concept.citations.length > 0 && (
              <p className="muted13">Cited from {concept.citations.length} source passage(s).</p>
            )}
          </div>
        </div>
      )}

      {error && <small className="errorText">{error}</small>}
      <button type="button" onClick={() => run(() => startTeaching(notebookId as string))} disabled={busy || !notebookId}>
        {busy ? "…" : session ? "Restart teaching session" : "Start teaching session"}
      </button>
    </section>
  );
}
