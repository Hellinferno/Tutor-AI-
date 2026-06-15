"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { Notification } from "../lib/types";

function describe(n: Notification): string {
  const p = n.payload as Record<string, string | number | null | undefined>;
  switch (n.kind) {
    case "notebook_shared":
      return `${p.owner_email ?? p.owner_id} shared "${p.notebook_title ?? p.notebook_id}" with you (${p.role}).`;
    case "assignment_created":
      return `New ${p.kind} in ${p.class_name ?? "your class"}: "${p.assignment_title}".`;
    case "submission_received":
      return `${p.student_email ?? p.student_id} submitted "${p.assignment_title}" in ${p.class_name ?? "your class"}.`;
    case "submission_graded":
      return `Feedback on "${p.assignment_title}" in ${p.class_name ?? "your class"}.`;
    case "comment_posted":
      return `${p.author_email ?? p.author_id} commented on "${p.notebook_title ?? p.notebook_id}".`;
    case "class_enrolled":
      return `${p.student_email ?? p.student_id} joined ${p.class_name ?? "your class"}.`;
    default:
      return n.kind;
  }
}

export function NotificationsPanel() {
  const { userEmail } = useNotebook();
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState<number>(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!userEmail) {
      setItems([]);
      setUnread(0);
      return;
    }
    try {
      const res = await listNotifications();
      setItems(res.notifications);
      setUnread(res.unread_count);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load notifications.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail]);

  async function markOne(id: string) {
    setBusy(true);
    try {
      await markNotificationRead(id);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function markAll() {
    setBusy(true);
    try {
      await markAllNotificationsRead();
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="notifications">
      <div className="panelHeader">
        <h3>Notifications</h3>
        <span className="badge">Phase 9{unread > 0 ? ` · ${unread}` : ""}</span>
      </div>

      {!userEmail && <p className="cardHint">Sign in to see notifications.</p>}

      {userEmail && (
        <>
          <div className="inlineForm">
            <button type="button" className="linkBtn" onClick={refresh} disabled={busy}>
              refresh
            </button>
            {unread > 0 && (
              <button type="button" className="linkBtn" onClick={markAll} disabled={busy}>
                mark all read
              </button>
            )}
          </div>
          {items.length === 0 && <small className="cardHint">You're all caught up.</small>}
          {items.map((n) => (
            <div className="sourceItem" key={n.id}>
              <strong style={{ opacity: n.read_at ? 0.6 : 1 }}>{describe(n)}</strong>
              <span>
                {new Date(n.created_at).toLocaleString()}
                {!n.read_at && (
                  <>
                    {" · "}
                    <button type="button" className="linkBtn" onClick={() => markOne(n.id)} disabled={busy}>
                      mark read
                    </button>
                  </>
                )}
              </span>
            </div>
          ))}
        </>
      )}

      {error && <small className="errorText">{error}</small>}
    </section>
  );
}
