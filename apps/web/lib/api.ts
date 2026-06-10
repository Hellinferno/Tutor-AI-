const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/v1";

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createNotebook(title: string) {
  return post("/notebooks", { title });
}

export function askNotebook(notebookId: string, query: string) {
  return post(`/notebooks/${notebookId}/ask`, { query });
}

export function solve(content: string, notebookId?: string) {
  return post("/solve", { input_type: "text", content, notebook_id: notebookId });
}

export function generateArtifact(notebookId: string, artifactType: string) {
  return post(`/notebooks/${notebookId}/artifacts/generate`, { artifact_type: artifactType });
}

// Phase 2: Teaching
export function startTeaching(notebookId: string) {
  return post(`/notebooks/${notebookId}/teaching/start`, {});
}

export function getTeachingSession(sessionId: string) {
  return get(`/teaching/${sessionId}`);
}

export function teachingNext(sessionId: string) {
  return post(`/teaching/${sessionId}/next`, {});
}

export function teachingPrev(sessionId: string) {
  return post(`/teaching/${sessionId}/prev`, {});
}

// Phase 2: Quizzes
export function generateQuiz(notebookId: string, numQuestions = 5, questionTypes?: string[], topic?: string) {
  return post(`/notebooks/${notebookId}/quizzes/generate`, {
    num_questions: numQuestions,
    question_types: questionTypes,
    topic,
  });
}

export function getQuiz(quizId: string, includeAnswers = false) {
  return get(`/quizzes/${quizId}${includeAnswers ? "?include_answers=true" : ""}`);
}

export function getQuizAnswerKey(quizId: string) {
  return post(`/quizzes/${quizId}/answer-key`, {});
}

export function submitQuizAttempt(quizId: string, answers: {question_id: string; answer: string}[]) {
  return post(`/quizzes/${quizId}/attempt`, { answers });
}

// Phase 2: Papers
export function generatePaper(notebookId: string, durationMinutes = 60, topic?: string) {
  return post(`/notebooks/${notebookId}/papers/generate`, { duration_minutes: durationMinutes, topic });
}

export function getPaper(paperId: string, includeAnswers = false) {
  return get(`/papers/${paperId}${includeAnswers ? "?include_answers=true" : ""}`);
}

export function getPaperAnswerKey(paperId: string) {
  return post(`/papers/${paperId}/answer-key`, {});
}

export function submitPaperAttempt(paperId: string, answers: {question_id: string; answer: string}[]) {
  return post(`/papers/${paperId}/attempt`, { answers });
}

// Phase 2: Reports
export function getReport(attemptId: string) {
  return get(`/reports/${attemptId}`);
}
