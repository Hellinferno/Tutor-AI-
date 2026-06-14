"use client";

import { useEffect, useState } from "react";
import { ApiError, getMe, loadAuthToken, login, registerUser, setAuthToken } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { AuthUser } from "../lib/types";

export function AuthPanel() {
  const { userEmail, setUser } = useNotebook();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore a saved session on first mount.
  useEffect(() => {
    if (!loadAuthToken()) return;
    getMe()
      .then((u: AuthUser) => setUser(u.id, u.email))
      .catch(() => setAuthToken(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const result = mode === "register" ? await registerUser(email, password) : await login(email, password);
      setAuthToken(result.token);
      setUser(result.user.id, result.user.email);
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    setAuthToken(null);
    setUser(null, null);
  }

  if (userEmail) {
    return (
      <section className="panel" id="account">
        <div className="panelHeader">
          <h3>Account</h3>
          <span className="badge">Phase 5</span>
        </div>
        <p className="muted13">
          Signed in as <strong>{userEmail}</strong>. Your notebooks, usage, and plan are scoped to this account.
        </p>
        <button type="button" className="secondary" onClick={logout}>
          Sign out
        </button>
      </section>
    );
  }

  return (
    <section className="panel" id="account">
      <div className="panelHeader">
        <h3>{mode === "register" ? "Create account" : "Sign in"}</h3>
        <span className="badge">Phase 5</span>
      </div>

      <div className="inputRow">
        <input
          className="textInput"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="textInput"
          type="password"
          placeholder="password (min 8 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </div>

      {error && <small className="errorText">{error}</small>}

      <button type="button" className="submitBtn" onClick={submit} disabled={busy || !email || !password}>
        {busy ? "…" : mode === "register" ? "Create account" : "Sign in"}
      </button>
      <button
        type="button"
        className="secondary"
        onClick={() => {
          setMode(mode === "register" ? "login" : "register");
          setError(null);
        }}
      >
        {mode === "register" ? "Have an account? Sign in" : "New here? Create an account"}
      </button>
      <p className="muted13">
        Optional — the app also works as a shared demo user. Sign in to scope data to your account (auth is enforced
        server‑side when <code>STUDYLAB_REQUIRE_AUTH</code> is set).
      </p>
    </section>
  );
}
