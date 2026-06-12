"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

interface NotebookContextValue {
  notebookId: string | null;
  notebookTitle: string;
  userId: string;
  lastAttemptId: string | null;
  setNotebook: (id: string, title: string) => void;
  setLastAttemptId: (id: string) => void;
}

const NotebookContext = createContext<NotebookContextValue | null>(null);

export function NotebookProvider({ children }: { children: ReactNode }) {
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const [notebookTitle, setNotebookTitle] = useState<string>("");
  const [lastAttemptId, setLastAttemptId] = useState<string | null>(null);

  function setNotebook(id: string, title: string) {
    setNotebookId(id);
    setNotebookTitle(title);
  }

  return (
    <NotebookContext.Provider
      value={{ notebookId, notebookTitle, userId: "demo-user", lastAttemptId, setNotebook, setLastAttemptId }}
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
