"use client";

import { useState } from "react";
import { ApiError, uploadSource } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { SourceGuide } from "../lib/types";

interface AddedSource {
  id: string;
  title: string;
  guide: SourceGuide;
}

export function SourcePanel() {
  const { notebookId } = useNotebook();
  const [title, setTitle] = useState("Gradient Descent");
  const [text, setText] = useState(
    "Gradient descent updates parameters by moving opposite the gradient of the loss. The update rule is theta := theta - eta * gradient. Net present value discounts each cash flow by the required return.",
  );
  const [sources, setSources] = useState<AddedSource[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload() {
    if (!notebookId || !text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await uploadSource(notebookId, title.trim() || "Untitled", text.trim());
      setSources((prev) => [{ id: result.source.id, title: result.source.title, guide: result.source_guide }, ...prev]);
      setText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="sources">
      <div className="panelHeader">
        <h3>Sources</h3>
        <span className="badge">{sources.length} uploaded</span>
      </div>

      {!notebookId ? (
        <p className="cardHint">Create a notebook first (top right).</p>
      ) : (
        <>
          <label className="inputRow">
            <span>Title</span>
            <input className="textInput" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="inputRow">
            <span>Paste notes / text</span>
            <textarea value={text} onChange={(e) => setText(e.target.value)} />
          </label>
          <button type="button" onClick={upload} disabled={busy || !text.trim()}>
            {busy ? "Uploading…" : "Upload source"}
          </button>
        </>
      )}

      {error && <small className="errorText">{error}</small>}

      {sources.map((s) => (
        <div className="guide" key={s.id}>
          <strong>{s.title}</strong>
          <p className="conceptExplanation">{s.guide.summary}</p>
          {s.guide.key_concepts.length > 0 && <p className="muted13">Concepts: {s.guide.key_concepts.join(", ")}</p>}
        </div>
      ))}
    </section>
  );
}
