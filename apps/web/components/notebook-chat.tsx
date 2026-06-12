"use client";

import { useState } from "react";
import { ApiError, askNotebook } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { AskResponse } from "../lib/types";

export function NotebookChat() {
  const { notebookId } = useNotebook();
  const [query, setQuery] = useState("How does gradient descent update parameters?");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(q?: string) {
    const question = (q ?? query).trim();
    if (!notebookId || !question) return;
    setBusy(true);
    setError(null);
    try {
      setAnswer(await askNotebook(notebookId, question));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ask failed.");
    } finally {
      setBusy(false);
    }
  }

  const refused = answer?.grounding === "insufficient_source_support";

  return (
    <section className="panel wide" id="ask">
      <div className="panelHeader">
        <h3>Ask your notebook</h3>
        <span className="badge">Citations required</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and upload a source first.</p>}

      {answer && (
        <div className="answer">
          <p className="eyebrow">{refused ? "Insufficient source support" : `Grounding: ${answer.grounding}`}</p>
          <p>{answer.answer}</p>
          {answer.citations.map((c, i) => (
            <div className="citationItem" key={`${c.source_id}-${i}`}>
              [{i + 1}] {c.source_title || c.source_id} · chunk {c.chunk_index} · score {c.score.toFixed(2)}
            </div>
          ))}
          {answer.suggested_followups.length > 0 && (
            <div className="followups">
              {answer.suggested_followups.map((f) => (
                <button type="button" key={f} onClick={() => { setQuery(f); ask(f); }}>
                  {f}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <label className="inputRow">
        <span>Question</span>
        <textarea value={query} onChange={(e) => setQuery(e.target.value)} disabled={!notebookId} />
      </label>
      {error && <small className="errorText">{error}</small>}
      <button type="button" onClick={() => ask()} disabled={busy || !notebookId || !query.trim()}>
        {busy ? "Asking…" : "Ask with sources"}
      </button>
    </section>
  );
}
