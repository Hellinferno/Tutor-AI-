"use client";

import { useState } from "react";
import { ApiError, generateQuiz, submitQuizAttempt } from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type { Attempt, Quiz } from "../lib/types";

const TYPES = [
  { key: "mcq", label: "Multiple choice" },
  { key: "true_false", label: "True/False" },
  { key: "short_answer", label: "Short answer" },
];

export function QuizPanel() {
  const { notebookId, setLastAttemptId } = useNotebook();
  const [selected, setSelected] = useState<string[]>(["mcq", "true_false"]);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleType(key: string) {
    setSelected((prev) => (prev.includes(key) ? prev.filter((t) => t !== key) : [...prev, key]));
  }

  async function generate() {
    if (!notebookId) return;
    setBusy(true);
    setError(null);
    setAttempt(null);
    try {
      const q = await generateQuiz(notebookId, 4, selected.length ? selected : undefined);
      setQuiz(q);
      setAnswers({});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Quiz generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!quiz) return;
    setBusy(true);
    setError(null);
    try {
      const payload = quiz.questions.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? "" }));
      const result = await submitQuizAttempt(quiz.id, payload);
      setAttempt(result);
      setLastAttemptId(result.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submit failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="quiz">
      <div className="panelHeader">
        <h3>Quiz generator</h3>
        <span className="badge">From your sources</span>
      </div>

      {!notebookId && <p className="cardHint">Create a notebook and upload a source first.</p>}

      <div className="quizGen">
        <button type="button" onClick={generate} disabled={busy || !notebookId}>
          {busy ? "…" : "Generate quiz"}
        </button>
        {TYPES.map((t) => (
          <button type="button" key={t.key} className="typeBtn" onClick={() => toggleType(t.key)}>
            {selected.includes(t.key) ? "✓ " : ""}
            {t.label}
          </button>
        ))}
      </div>

      {quiz?.questions.map((q, i) => {
        const scored = attempt?.answers.find((a) => a.question_id === q.id);
        return (
          <div className="quizQuestion" key={q.id}>
            <p className="eyebrow">
              Question {i + 1} · {q.points} pts
            </p>
            <p>{q.question_text}</p>
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
            {scored && (
              <p className={scored.correct ? "strongTag" : "weakTag"}>{scored.feedback}</p>
            )}
          </div>
        );
      })}

      {error && <small className="errorText">{error}</small>}

      {quiz && !attempt && (
        <button type="button" className="submitBtn" onClick={submit} disabled={busy}>
          Submit answers
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
