"use client";

import { useState } from "react";
import { ApiError, generatePaper, submitPaperAttempt } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { Attempt, QuestionPaper } from "../lib/types";

export function PaperPanel() {
  const { notebookId, setLastAttemptId } = useNotebook();
  const [paper, setPaper] = useState<QuestionPaper | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    if (!notebookId) return;
    setBusy(true);
    setError(null);
    setAttempt(null);
    try {
      const p = await generatePaper(notebookId, 45);
      setPaper(p);
      setAnswers({});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Paper generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!paper) return;
    setBusy(true);
    setError(null);
    try {
      const all = paper.sections.flatMap((s) => s.questions);
      const payload = all.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? "" }));
      const result = await submitPaperAttempt(paper.id, payload);
      setAttempt(result);
      setLastAttemptId(result.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submit failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel wide" id="papers">
      <div className="panelHeader">
        <h3>Question paper</h3>
        <span className="badge">Exam mode</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and upload a source first.</p>}

      {paper && (
        <>
          <div className="paperHeader">
            <span>
              <strong>Duration:</strong> {paper.duration_minutes} min
            </span>
            <span>
              <strong>Sections:</strong> {paper.sections.length}
            </span>
            <span>
              <strong>Total marks:</strong> {paper.total_marks}
            </span>
          </div>
          {paper.sections.map((section, si) => (
            <div className="paperSection" key={si}>
              <p className="eyebrow">{section.title}</p>
              <p>{section.instructions}</p>
              {section.questions.map((q, qi) => (
                <div className="quizQuestion" key={q.id}>
                  <p>
                    {qi + 1}. {q.question_text} <small>({q.points} pts)</small>
                  </p>
                  {q.options ? (
                    <div className="quizOptions">
                      {q.options.map((opt) => (
                        <label key={opt}>
                          <input
                            type="radio"
                            name={q.id}
                            checked={answers[q.id] === opt}
                            onChange={() => setAnswers((p) => ({ ...p, [q.id]: opt }))}
                          />
                          {opt}
                        </label>
                      ))}
                    </div>
                  ) : (
                    <input
                      className="textInput"
                      placeholder="Your answer"
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((p) => ({ ...p, [q.id]: e.target.value }))}
                    />
                  )}
                </div>
              ))}
            </div>
          ))}
        </>
      )}

      {error && <small className="errorText">{error}</small>}

      <button type="button" onClick={generate} disabled={busy || !notebookId}>
        {busy ? "…" : "Generate question paper"}
      </button>
      {paper && !attempt && (
        <button type="button" className="secondary" onClick={submit} disabled={busy}>
          Submit paper
        </button>
      )}
      {attempt && (
        <div className="solveResult">
          <span>Score</span>
          <strong>
            {attempt.total_score} / {attempt.max_score}
          </strong>
          <small>Open the Reports panel for the full breakdown.</small>
        </div>
      )}
    </section>
  );
}
