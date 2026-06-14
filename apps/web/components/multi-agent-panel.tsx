"use client";

import { useState } from "react";
import { ApiError, agentTeachingNext, agentTeachingPrev, startAgentTeaching } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { MultiAgentTeachingSession } from "../lib/types";

const ROLE_LABELS: Record<string, string> = {
  concept_explainer: "🧑‍🏫 Explainer",
  grounding_verifier: "✅ Verifier",
  practice_coach: "🏋️ Coach",
};

export function MultiAgentPanel() {
  const { notebookId } = useNotebook();
  const [session, setSession] = useState<MultiAgentTeachingSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<MultiAgentTeachingSession>) {
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

  const idx = session?.current_concept_idx ?? 0;
  const concept = session?.concepts[idx];
  const turns = session?.agent_turns.filter((t) => t.concept_index === idx) ?? [];

  return (
    <section className="panel wide" id="agents">
      <div className="panelHeader">
        <h3>Multi-agent teaching</h3>
        <span className="badge">Phase 4</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and add a source first.</p>}

      {session && concept && (
        <div className="conceptDisplay">
          <div className="conceptNav">
            <button type="button" onClick={() => run(() => agentTeachingPrev(session.id))} disabled={busy || idx === 0}>
              ← Previous
            </button>
            <span className="conceptCounter">
              {idx + 1} / {session.concepts.length}
            </span>
            <button
              type="button"
              onClick={() => run(() => agentTeachingNext(session.id))}
              disabled={busy || idx >= session.concepts.length - 1}
            >
              Next →
            </button>
          </div>
          <strong className="conceptName">{concept.name}</strong>
          <div className="agentTurns">
            {turns.map((turn, i) => (
              <div className="agentTurn" key={i}>
                <div className="agentTurnHead">
                  <span className="agentRole">{ROLE_LABELS[turn.role] ?? turn.role}</span>
                  <span className="agentConf">{Math.round(turn.confidence * 100)}%</span>
                </div>
                <p className="agentTitle">{turn.title}</p>
                <p className="muted13">{turn.content}</p>
                {turn.citations.length > 0 && (
                  <small>Grounded in {turn.citations.length} cited passage(s).</small>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <small className="errorText">{error}</small>}
      <button type="button" onClick={() => run(() => startAgentTeaching(notebookId as string))} disabled={busy || !notebookId}>
        {busy ? "…" : session ? "Restart agent session" : "Start agent teaching"}
      </button>
    </section>
  );
}
