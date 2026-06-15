"use client";

import { useEffect, useState } from "react";
import { ApiError, listShares, listSharedWithMe, shareNotebook, unshareNotebook } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { NotebookShare, ShareRole, SharedWithItem } from "../lib/types";

export function SharePanel() {
  const { notebookId, notebookTitle, userEmail, setNotebook } = useNotebook();
  const [shares, setShares] = useState<NotebookShare[]>([]);
  const [sharedWithMe, setSharedWithMe] = useState<SharedWithItem[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ShareRole>("viewer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshShares() {
    if (!notebookId || !userEmail) {
      setShares([]);
      return;
    }
    try {
      setShares((await listShares(notebookId)).shares);
    } catch {
      // Not the owner (or not logged in) — sharing controls don't apply.
      setShares([]);
    }
  }

  async function refreshSharedWithMe() {
    if (!userEmail) {
      setSharedWithMe([]);
      return;
    }
    try {
      setSharedWithMe((await listSharedWithMe()).shared_with_me);
    } catch {
      setSharedWithMe([]);
    }
  }

  useEffect(() => {
    refreshShares();
    refreshSharedWithMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebookId, userEmail]);

  async function addShare() {
    if (!notebookId || !email.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await shareNotebook(notebookId, email.trim(), role);
      setEmail("");
      await refreshShares();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Share failed.");
    } finally {
      setBusy(false);
    }
  }

  async function removeShare(shareId: string) {
    if (!notebookId) return;
    setBusy(true);
    setError(null);
    try {
      await unshareNotebook(notebookId, shareId);
      await refreshShares();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Remove failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="share">
      <div className="panelHeader">
        <h3>Sharing</h3>
        <span className="badge">Phase 7</span>
      </div>

      {!userEmail && <p className="cardHint">Sign in to share notebooks and see what's shared with you.</p>}

      {userEmail && notebookId && (
        <div className="spaced">
          <span className="muted13">
            Share <strong>{notebookTitle}</strong> (you must be the owner)
          </span>
          <div className="inlineForm">
            <input className="textInput" type="email" placeholder="collaborator@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            <select className="textInput" value={role} onChange={(e) => setRole(e.target.value as ShareRole)}>
              <option value="viewer">viewer</option>
              <option value="editor">editor</option>
            </select>
            <button type="button" className="submitBtn" onClick={addShare} disabled={busy || !email.trim()}>
              Share
            </button>
          </div>
          {shares.map((s) => (
            <div className="sourceItem" key={s.id}>
              <strong>{s.shared_with_email}</strong>
              <span>
                {s.role}
                {" · "}
                <button type="button" className="linkBtn" onClick={() => removeShare(s.id)} disabled={busy}>
                  remove
                </button>
              </span>
            </div>
          ))}
        </div>
      )}

      {error && <small className="errorText">{error}</small>}

      {userEmail && (
        <div className="spaced">
          <span className="muted13">Shared with me</span>
          {sharedWithMe.length === 0 && <small className="cardHint">Nothing shared with you yet.</small>}
          {sharedWithMe.map((item) => (
            <div className="sourceItem" key={item.share_id}>
              <strong>{item.title}</strong>
              <span>
                {item.role}
                {" · "}
                <button type="button" className="linkBtn" onClick={() => setNotebook(item.notebook_id, item.title)}>
                  open
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
