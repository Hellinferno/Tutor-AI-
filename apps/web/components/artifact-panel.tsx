"use client";

import { useState } from "react";
import { ApiError, generateArtifact } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { Artifact } from "../lib/types";

const ARTIFACTS = [
  { key: "summary_notes", label: "Summary" },
  { key: "study_guide", label: "Study guide" },
  { key: "planner", label: "Planner" },
  { key: "timetable", label: "Timetable" },
  { key: "revision_cards", label: "Revision" },
];

export function ArtifactPanel() {
  const { notebookId } = useNotebook();
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function generate(type: string) {
    if (!notebookId) return;
    setBusyKey(type);
    setError(null);
    try {
      setArtifact(await generateArtifact(notebookId, type));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed.");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="panel wide" id="artifacts">
      <div className="panelHeader">
        <h3>Study artifacts</h3>
        <span className="badge">From source guides</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and upload a source first.</p>}

      <div className="artifactButtons">
        {ARTIFACTS.map((a) => (
          <button type="button" key={a.key} onClick={() => generate(a.key)} disabled={!notebookId || busyKey !== null}>
            {busyKey === a.key ? "…" : a.label}
          </button>
        ))}
      </div>

      {error && <small className="errorText">{error}</small>}

      {artifact && (
        <div className="notionBox">
          <strong>{artifact.title}</strong>
          <div className="markdownBox">{artifact.content_markdown}</div>
        </div>
      )}
    </section>
  );
}
