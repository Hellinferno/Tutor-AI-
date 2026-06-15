"use client";

import { useEffect, useState } from "react";
import { ApiError, listNotebookComments, postNotebookComment } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { NotebookComment } from "../lib/types";

export function DiscussionsPanel() {
  const { notebookId, notebookTitle, userEmail } = useNotebook();
  const [comments, setComments] = useState<NotebookComment[]>([]);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!notebookId || !userEmail) {
      setComments([]);
      return;
    }
    try {
      setComments((await listNotebookComments(notebookId)).comments);
    } catch (err) {
      // Likely "no access" — discussion controls don't apply.
      setComments([]);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebookId, userEmail]);

  async function submit() {
    if (!notebookId || !body.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await postNotebookComment(notebookId, body.trim());
      setBody("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't post comment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="discuss">
      <div className="panelHeader">
        <h3>Discussion</h3>
        <span className="badge">Phase 9</span>
      </div>

      {!userEmail && <p className="cardHint">Sign in to read or post comments.</p>}
      {userEmail && !notebookId && <p className="cardHint">Pick a notebook to start the discussion.</p>}

      {userEmail && notebookId && (
        <>
          <span className="muted13">
            Comments on <strong>{notebookTitle}</strong> (visible to the owner and anyone the notebook is shared with)
          </span>
          <div className="inlineForm">
            <input
              className="textInput"
              placeholder="Share a thought or question…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={8000}
            />
            <button type="button" className="submitBtn" onClick={submit} disabled={busy || !body.trim()}>
              Post
            </button>
          </div>
          {comments.length === 0 && <small className="cardHint">No comments yet — be the first.</small>}
          {comments.map((c) => (
            <div className="sourceItem" key={c.id}>
              <strong>{c.author_email ?? c.author_id.slice(0, 8)}</strong>
              <span style={{ whiteSpace: "pre-wrap" }}>{c.body}</span>
              <small className="cardHint">{new Date(c.created_at).toLocaleString()}</small>
            </div>
          ))}
        </>
      )}

      {error && <small className="errorText">{error}</small>}
    </section>
  );
}
