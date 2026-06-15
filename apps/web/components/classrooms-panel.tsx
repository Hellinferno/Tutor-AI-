"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  createAssignment,
  createClass,
  enrollInClass,
  generateQuiz,
  getClassAnalytics,
  getClassRoster,
  listAssignmentSubmissions,
  listClassAssignments,
  listMyAssignments,
  listMyClasses,
  submitAssignment,
} from "../lib/api";
import { useNotebook } from "../lib/notebook-context";
import type {
  Assignment,
  AssignmentKind,
  AssignmentSubmissionsResponse,
  ClassAnalyticsResponse,
  ClassAssignmentsResponse,
  ClassroomClass,
  EnrolledClassItem,
  RosterResponse,
} from "../lib/types";

export function ClassroomsPanel() {
  const { notebookId, userEmail, setLastAttemptId } = useNotebook();
  const [teaching, setTeaching] = useState<ClassroomClass[]>([]);
  const [enrolled, setEnrolled] = useState<EnrolledClassItem[]>([]);
  const [myAssignments, setMyAssignments] = useState<Assignment[]>([]);
  const [className, setClassName] = useState("");
  const [enrollCode, setEnrollCode] = useState("");
  const [activeClassId, setActiveClassId] = useState<string | null>(null);
  const [classView, setClassView] = useState<ClassAssignmentsResponse | null>(null);
  const [roster, setRoster] = useState<RosterResponse | null>(null);
  const [analytics, setAnalytics] = useState<ClassAnalyticsResponse | null>(null);
  const [submissions, setSubmissions] = useState<AssignmentSubmissionsResponse | null>(null);
  const [assignTitle, setAssignTitle] = useState("");
  const [assignDue, setAssignDue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshHome() {
    if (!userEmail) {
      setTeaching([]);
      setEnrolled([]);
      setMyAssignments([]);
      return;
    }
    try {
      const mine = await listMyClasses();
      setTeaching(mine.teaching);
      setEnrolled(mine.enrolled);
    } catch {
      setTeaching([]);
      setEnrolled([]);
    }
    try {
      const a = await listMyAssignments();
      setMyAssignments(a.assignments);
    } catch {
      setMyAssignments([]);
    }
  }

  async function refreshActiveClass() {
    if (!activeClassId) {
      setClassView(null);
      setRoster(null);
      setAnalytics(null);
      return;
    }
    try {
      setClassView(await listClassAssignments(activeClassId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load class.");
      setClassView(null);
    }
    try {
      setRoster(await getClassRoster(activeClassId));
    } catch {
      setRoster(null);
    }
    try {
      setAnalytics(await getClassAnalytics(activeClassId));
    } catch {
      setAnalytics(null);
    }
  }

  useEffect(() => {
    refreshHome();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail]);

  useEffect(() => {
    refreshActiveClass();
    setSubmissions(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeClassId]);

  async function handleCreateClass() {
    if (!className.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createClass(className.trim());
      setClassName("");
      await refreshHome();
      setActiveClassId(created.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create class failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEnroll() {
    if (!enrollCode.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await enrollInClass(enrollCode.trim().toUpperCase());
      setEnrollCode("");
      await refreshHome();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enroll failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateAssignment(kind: AssignmentKind) {
    if (!activeClassId || !notebookId || !assignTitle.trim()) {
      setError("Pick a notebook, set a title, and select a class first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // For demo purposes, generate a fresh quiz from the current notebook so the
      // instructor doesn't have to copy a quiz id by hand. Papers follow the same
      // pattern via the Papers panel; if the user wants to assign a paper here,
      // they need to wire its id (kept intentionally simple in this Phase 8 UI).
      if (kind === "quiz") {
        const quiz = await generateQuiz(notebookId, 4);
        await createAssignment(activeClassId, "quiz", quiz.id, assignTitle.trim(), assignDue || null);
      } else {
        setError("Generate the paper in the Papers panel, then copy its id into the API.");
        return;
      }
      setAssignTitle("");
      setAssignDue("");
      await refreshActiveClass();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create assignment failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleViewSubmissions(assignmentId: string) {
    setBusy(true);
    setError(null);
    try {
      setSubmissions(await listAssignmentSubmissions(assignmentId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load submissions.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitAssignment(assignment: Assignment) {
    // Submitting an assignment with empty answers is a "mark seen" smoke path.
    // The student normally takes the quiz in the Quiz panel; this panel scores
    // their visit so the instructor can see they engaged.
    setBusy(true);
    setError(null);
    try {
      const result = await submitAssignment(assignment.id, []);
      setLastAttemptId(result.attempt.id);
      await refreshHome();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submit failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="classes">
      <div className="panelHeader">
        <h3>Classrooms</h3>
        <span className="badge">Phase 8</span>
      </div>

      {!userEmail && <p className="cardHint">Sign in to instruct classes, enroll, or complete assignments.</p>}

      {userEmail && (
        <>
          <div className="spaced">
            <span className="muted13">Create a class (requires instructor role)</span>
            <div className="inlineForm">
              <input className="textInput" placeholder="Class name" value={className} onChange={(e) => setClassName(e.target.value)} />
              <button type="button" className="submitBtn" onClick={handleCreateClass} disabled={busy || !className.trim()}>
                Create
              </button>
            </div>
            <span className="muted13">Enroll with a join code</span>
            <div className="inlineForm">
              <input
                className="textInput"
                placeholder="ABC123"
                value={enrollCode}
                onChange={(e) => setEnrollCode(e.target.value.toUpperCase())}
                maxLength={8}
              />
              <button type="button" className="submitBtn" onClick={handleEnroll} disabled={busy || !enrollCode.trim()}>
                Join
              </button>
            </div>
          </div>

          {teaching.length > 0 && (
            <div className="spaced">
              <span className="muted13">Teaching</span>
              {teaching.map((c) => (
                <div className="sourceItem" key={c.id}>
                  <strong>{c.name}</strong>
                  <span>
                    code <code>{c.code}</code>
                    {" · "}
                    <button type="button" className="linkBtn" onClick={() => setActiveClassId(c.id)}>
                      manage
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}

          {enrolled.length > 0 && (
            <div className="spaced">
              <span className="muted13">Enrolled</span>
              {enrolled.map((c) => (
                <div className="sourceItem" key={c.id}>
                  <strong>{c.name}</strong>
                  <span>
                    <button type="button" className="linkBtn" onClick={() => setActiveClassId(c.id)}>
                      open
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}

          {classView && (
            <div className="spaced">
              <span className="muted13">
                <strong>{classView.class.name}</strong> · code <code>{classView.class.code}</code>
              </span>
              {roster && (
                <small className="cardHint">
                  Roster: {roster.roster.length} student{roster.roster.length === 1 ? "" : "s"}
                  {roster.roster.length > 0 && ` — ${roster.roster.map((r) => r.email ?? r.student_id.slice(0, 8)).join(", ")}`}
                </small>
              )}
              <div className="inlineForm">
                <input
                  className="textInput"
                  placeholder="Assignment title"
                  value={assignTitle}
                  onChange={(e) => setAssignTitle(e.target.value)}
                />
                <input
                  className="textInput"
                  type="datetime-local"
                  value={assignDue}
                  onChange={(e) => setAssignDue(e.target.value)}
                />
                <button
                  type="button"
                  className="submitBtn"
                  onClick={() => handleCreateAssignment("quiz")}
                  disabled={busy || !assignTitle.trim() || !notebookId}
                >
                  Generate quiz + assign
                </button>
              </div>
              {classView.assignments.map((a) => (
                <div className="sourceItem" key={a.id}>
                  <strong>{a.title}</strong>
                  <span>
                    {a.kind}
                    {a.due_at ? ` · due ${new Date(a.due_at).toLocaleString()}` : ""}
                    {typeof a.submission_count === "number" && ` · ${a.submission_count} submission${a.submission_count === 1 ? "" : "s"}`}
                    {" · "}
                    <button type="button" className="linkBtn" onClick={() => handleViewSubmissions(a.id)}>
                      view submissions
                    </button>
                  </span>
                </div>
              ))}
              {analytics && (
                <small className="cardHint">
                  Overall avg: {analytics.overall_avg_percentage ?? "—"}% · {analytics.enrolled_count} enrolled ·{" "}
                  {analytics.assignment_count} assignment{analytics.assignment_count === 1 ? "" : "s"}
                  {analytics.top_weak_topics.length > 0 && ` · top weak: ${analytics.top_weak_topics.join(", ")}`}
                </small>
              )}
            </div>
          )}

          {submissions && (
            <div className="spaced">
              <span className="muted13">
                Submissions for <strong>{submissions.assignment.title}</strong>
              </span>
              {submissions.submissions.length === 0 && <small className="cardHint">No submissions yet.</small>}
              {submissions.submissions.map((s) => (
                <div className="sourceItem" key={s.submission_id}>
                  <strong>{s.email ?? s.student_id.slice(0, 8)}</strong>
                  <span>
                    {Math.round((s.total_score / Math.max(s.max_score, 1)) * 1000) / 10}% ({s.total_score}/{s.max_score})
                    {" · "}
                    {new Date(s.submitted_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          {myAssignments.length > 0 && (
            <div className="spaced">
              <span className="muted13">My assignments</span>
              {myAssignments.map((a) => (
                <div className="sourceItem" key={a.id}>
                  <strong>{a.title}</strong>
                  <span>
                    {a.class_name ? `${a.class_name} · ` : ""}
                    {a.kind}
                    {a.due_at ? ` · due ${new Date(a.due_at).toLocaleString()}` : ""}
                    {a.submitted
                      ? ` · submitted ${Math.round(((a.total_score ?? 0) / Math.max(a.max_score ?? 1, 1)) * 1000) / 10}%`
                      : " · not submitted"}
                    {!a.submitted && (
                      <>
                        {" · "}
                        <button type="button" className="linkBtn" onClick={() => handleSubmitAssignment(a)} disabled={busy}>
                          mark submitted
                        </button>
                      </>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {error && <small className="errorText">{error}</small>}
    </section>
  );
}
