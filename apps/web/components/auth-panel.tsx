"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  changePassword,
  deleteAccount,
  getMe,
  loadAuthToken,
  login,
  registerUser,
  requestPasswordReset,
  resetPassword,
  setAuthToken,
  updateProfile,
} from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { AuthUser } from "../lib/types";

const SUBJECTS = ["ai_ds", "analytics", "finance"];

export function AuthPanel() {
  const { userEmail, setUser } = useNotebook();
  const [mode, setMode] = useState<"login" | "register" | "forgot" | "reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  // Signed-in account management
  const [me, setMe] = useState<AuthUser | null>(null);
  const [showAccount, setShowAccount] = useState(false);
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");

  useEffect(() => {
    if (!loadAuthToken()) return;
    getMe()
      .then((u) => {
        setUser(u.id, u.email);
        setMe(u);
      })
      .catch(() => setAuthToken(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function reset() {
    setError(null);
    setNote(null);
  }

  async function submitAuth() {
    setBusy(true);
    reset();
    try {
      const result = mode === "register" ? await registerUser(email, password) : await login(email, password);
      setAuthToken(result.token);
      setUser(result.user.id, result.user.email);
      setMe(result.user);
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitForgot() {
    setBusy(true);
    reset();
    try {
      const r = await requestPasswordReset(email);
      // Mock mode returns the token directly; production emails it.
      if (r.reset_token) {
        setResetToken(r.reset_token);
        setMode("reset");
        setNote("Reset token issued (mock email). Enter a new password.");
      } else {
        setNote("If that email exists, a reset link has been sent.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start password reset.");
    } finally {
      setBusy(false);
    }
  }

  async function submitReset() {
    setBusy(true);
    reset();
    try {
      await resetPassword(resetToken, password);
      setNote("Password reset. You can now sign in.");
      setMode("login");
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reset failed.");
    } finally {
      setBusy(false);
    }
  }

  async function doChangePassword() {
    setBusy(true);
    reset();
    try {
      await changePassword(curPw, newPw);
      setNote("Password changed.");
      setCurPw("");
      setNewPw("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Change failed.");
    } finally {
      setBusy(false);
    }
  }

  async function changeSubject(subject: string) {
    reset();
    try {
      setMe(await updateProfile(subject));
      setNote("Profile updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed.");
    }
  }

  function logout() {
    setAuthToken(null);
    setUser(null, null);
    setMe(null);
    setShowAccount(false);
  }

  async function doDelete() {
    if (typeof window !== "undefined" && !window.confirm("Delete your account and all its data? This cannot be undone.")) return;
    setBusy(true);
    reset();
    try {
      await deleteAccount();
      logout();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  // ── Signed in ──
  if (userEmail) {
    return (
      <section className="panel" id="account">
        <div className="panelHeader">
          <h3>Account</h3>
          <span className="badge">Phase 5–6</span>
        </div>
        <p className="muted13">
          Signed in as <strong>{userEmail}</strong>. Your notebooks, usage, and plan are scoped to this account.
        </p>
        {me && (
          <label className="inputRow">
            <span>Subject focus</span>
            <select className="textInput" value={me.subject_domain} onChange={(e) => changeSubject(e.target.value)}>
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
        )}
        <button type="button" className="secondary" onClick={() => setShowAccount(!showAccount)}>
          {showAccount ? "Hide account settings" : "Account settings"}
        </button>
        {showAccount && (
          <div className="spaced">
            <div className="inputRow">
              <span>Change password</span>
              <input className="textInput" type="password" placeholder="current password" value={curPw} onChange={(e) => setCurPw(e.target.value)} />
              <input className="textInput" type="password" placeholder="new password (min 8)" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
              <button type="button" className="submitBtn" onClick={doChangePassword} disabled={busy || !curPw || !newPw}>
                Update password
              </button>
            </div>
            <button type="button" className="forgotBtn" onClick={doDelete} disabled={busy}>
              Delete account
            </button>
          </div>
        )}
        {note && <small className="muted13">{note}</small>}
        {error && <small className="errorText">{error}</small>}
        <button type="button" className="secondary" onClick={logout}>
          Sign out
        </button>
      </section>
    );
  }

  // ── Signed out ──
  return (
    <section className="panel" id="account">
      <div className="panelHeader">
        <h3>
          {mode === "register" ? "Create account" : mode === "forgot" ? "Reset password" : mode === "reset" ? "Set new password" : "Sign in"}
        </h3>
        <span className="badge">Phase 5–6</span>
      </div>

      {mode === "reset" ? (
        <div className="inputRow">
          <input className="textInput" placeholder="reset token" value={resetToken} onChange={(e) => setResetToken(e.target.value)} />
          <input className="textInput" type="password" placeholder="new password (min 8)" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
      ) : (
        <div className="inputRow">
          <input className="textInput" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          {mode !== "forgot" && (
            <input
              className="textInput"
              type="password"
              placeholder="password (min 8 chars)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitAuth()}
            />
          )}
        </div>
      )}

      {note && <small className="muted13">{note}</small>}
      {error && <small className="errorText">{error}</small>}

      {mode === "forgot" ? (
        <button type="button" className="submitBtn" onClick={submitForgot} disabled={busy || !email}>
          {busy ? "…" : "Send reset token"}
        </button>
      ) : mode === "reset" ? (
        <button type="button" className="submitBtn" onClick={submitReset} disabled={busy || !resetToken || !password}>
          {busy ? "…" : "Set new password"}
        </button>
      ) : (
        <button type="button" className="submitBtn" onClick={submitAuth} disabled={busy || !email || !password}>
          {busy ? "…" : mode === "register" ? "Create account" : "Sign in"}
        </button>
      )}

      <div className="followups">
        <button type="button" onClick={() => { setMode(mode === "register" ? "login" : "register"); reset(); }}>
          {mode === "register" ? "Have an account? Sign in" : "New here? Create an account"}
        </button>
        {mode !== "forgot" && mode !== "reset" && (
          <button type="button" onClick={() => { setMode("forgot"); reset(); }}>
            Forgot password?
          </button>
        )}
      </div>

      <p className="muted13">
        Optional — the app also works as a shared demo user. Sign in to scope data to your account (auth is enforced
        server‑side when <code>STUDYLAB_REQUIRE_AUTH</code> is set).
      </p>
    </section>
  );
}
