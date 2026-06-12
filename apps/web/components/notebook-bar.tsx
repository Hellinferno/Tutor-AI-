"use client";

import { useState } from "react";
import { ApiError, createNotebook } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";

export function NotebookBar() {
  const { notebookId, notebookTitle, setNotebook } = useNotebook();
  const [title, setTitle] = useState("Machine Learning 101");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    if (!title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const nb = await createNotebook(title.trim());
      setNotebook(nb.id, nb.title);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the gateway. Is it running on :8000?");
    } finally {
      setBusy(false);
    }
  }

  if (notebookId) {
    return (
      <span className="status" title={notebookId}>
        📓 {notebookTitle} · <small>{notebookId}</small>
      </span>
    );
  }

  return (
    <div className="inputRow notebookCreate">
      <span>Create a notebook to begin</span>
      <div className="inlineForm">
        <input className="textInput" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Notebook title" />
        <button type="button" onClick={create} disabled={busy}>
          {busy ? "…" : "Create"}
        </button>
      </div>
      {error && <small className="errorText">{error}</small>}
    </div>
  );
}
