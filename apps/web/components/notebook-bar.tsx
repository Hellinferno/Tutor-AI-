"use client";

import { useState } from "react";
import { ApiError, createNotebook, uploadSource } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";

const SAMPLE_TEXT =
  "Gradient descent updates parameters by moving opposite the gradient of the loss function. " +
  "The update rule is theta := theta - eta * gradient, where eta is the learning rate. " +
  "Feature scaling helps convergence. Net present value (NPV) discounts each future cash flow " +
  "by the required rate of return and sums them to value an investment today.";

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

  async function loadSample() {
    setBusy(true);
    setError(null);
    try {
      const nb = await createNotebook("Sample · Gradient Descent & NPV");
      await uploadSource(nb.id, "Sample notes", SAMPLE_TEXT);
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
      <span>Create a notebook to begin — or load a sample to explore instantly</span>
      <div className="inlineForm">
        <input className="textInput" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Notebook title" />
        <button type="button" onClick={create} disabled={busy}>
          {busy ? "…" : "Create"}
        </button>
        <button type="button" className="secondary" onClick={loadSample} disabled={busy}>
          {busy ? "…" : "Load sample"}
        </button>
      </div>
      {error && <small className="errorText">{error}</small>}
    </div>
  );
}
