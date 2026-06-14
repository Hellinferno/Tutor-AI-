"use client";

import { useEffect, useState } from "react";
import { ApiError, importSource, listImports } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { ConnectorType, SourceImport } from "../lib/types";

const CONNECTORS: { type: ConnectorType; label: string; field: string; placeholder: string }[] = [
  { type: "website", label: "Website", field: "extracted_text", placeholder: "Paste the article text (or HTML) extracted from the page…" },
  { type: "youtube", label: "YouTube", field: "transcript", placeholder: "Paste the video transcript / captions…" },
  { type: "audio", label: "Audio", field: "transcript", placeholder: "Paste the audio transcript…" },
  { type: "google_doc", label: "Google Doc", field: "exported_text", placeholder: "Paste the exported document text…" },
  { type: "google_slides", label: "Google Slides", field: "exported_text", placeholder: "Paste the exported slides text…" },
];

export function ConnectorsPanel() {
  const { notebookId } = useNotebook();
  const [type, setType] = useState<ConnectorType>("website");
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [imports, setImports] = useState<SourceImport[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const active = CONNECTORS.find((c) => c.type === type)!;

  async function refresh() {
    if (!notebookId) return;
    try {
      setImports((await listImports(notebookId)).imports);
    } catch {
      /* ignore refresh errors */
    }
  }

  useEffect(() => {
    setImports([]);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebookId]);

  async function runImport() {
    if (!notebookId) return;
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = { [active.field]: content };
      if (url.trim()) payload.url = url.trim();
      if (type === "youtube" && url.trim()) payload.video_id = url.trim().split("v=")[1] ?? undefined;
      await importSource(notebookId, type, title, payload);
      setContent("");
      setUrl("");
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed.");
    } finally {
      setBusy(false);
    }
  }

  const needsUrl = type === "website" || type === "youtube" || type === "google_doc" || type === "google_slides";

  return (
    <section className="panel wide" id="connectors">
      <div className="panelHeader">
        <h3>Source connectors</h3>
        <span className="badge">Phase 4</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook first.</p>}

      <div className="connectorTabs">
        {CONNECTORS.map((c) => (
          <button
            key={c.type}
            type="button"
            className={c.type === type ? "typeBtn active" : "typeBtn"}
            onClick={() => setType(c.type)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="inputRow">
        {needsUrl && (
          <input
            className="textInput"
            placeholder={type === "youtube" ? "https://youtube.com/watch?v=…" : "https://… (source URL)"}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        )}
        <input className="textInput" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea placeholder={active.placeholder} value={content} onChange={(e) => setContent(e.target.value)} />
      </div>

      <p className="muted13">
        The core never fetches remote content directly — a connector worker extracts text, transcript, or exported
        content, then it is chunked, guided, and cited exactly like an upload.
      </p>

      {error && <small className="errorText">{error}</small>}
      <button type="button" className="submitBtn" onClick={runImport} disabled={busy || !notebookId || !content.trim()}>
        {busy ? "Importing…" : `Import from ${active.label}`}
      </button>

      {imports.length > 0 && (
        <div className="spaced">
          {imports.map((imp) => (
            <div className="sourceItem" key={imp.id}>
              <strong>{imp.title}</strong>
              <span>
                {imp.connector_type} · {imp.status}
                {imp.warnings.length > 0 ? ` · ${imp.warnings.length} note(s)` : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
