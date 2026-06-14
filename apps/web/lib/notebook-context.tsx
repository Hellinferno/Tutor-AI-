"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

interface NotebookContextValue {
  notebookId: string | null;
  notebookTitle: string;
  userId: string;
  userEmail: string | null;
  lastAttemptId: string | null;
  setNotebook: (id: string, title: string) => void;
  setLastAttemptId: (id: string) => void;
  setUser: (id: string | null, email: string | null) => void;
}

const NotebookContext = createContext<NotebookContextValue | null>(null);

export function NotebookProvider({ children }: { children: ReactNode }) {
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const [notebookTitle, setNotebookTitle] = useState<string>("");
  const [lastAttemptId, setLastAttemptId] = useState<string | null>(null);
  // Defaults to the demo user so the app works without logging in; the auth panel
  // swaps in the real user id/email once a session is established.
  const [userId, setUserId] = useState<string>("demo-user");
  const [userEmail, setUserEmail] = useState<string | null>(null);

  function setNotebook(id: string, title: string) {
    setNotebookId(id);
    setNotebookTitle(title);
  }

  function setUser(id: string | null, email: string | null) {
    setUserId(id ?? "demo-user");
    setUserEmail(email);
  }

  return (
    <NotebookContext.Provider
      value={{ notebookId, notebookTitle, userId, userEmail, lastAttemptId, setNotebook, setLastAttemptId, setUser }}
    >
      {children}
    </NotebookContext.Provider>
  );
}

export function useNotebook(): NotebookContextValue {
  const value = useContext(NotebookContext);
  if (!value) {
    throw new Error("useNotebook must be used inside <NotebookProvider>");
  }
  return value;
}
