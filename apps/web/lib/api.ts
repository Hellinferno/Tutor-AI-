import type {
  AnswerKey,
  Artifact,
  AskResponse,
  Attempt,
  CardStats,
  EvalReport,
  KnowledgeState,
  Notebook,
  QuestionPaper,
  Quiz,
  RevisionCard,
  SolveResponse,
  SolveStep,
  TrendPoint,
  UploadResult,
  UserSummary,
  VoiceResult,
  WhiteboardSession,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return body?.error?.message ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new ApiError(response.status, await readError(response));
  return response.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new ApiError(response.status, await readError(response));
  return response.json() as Promise<T>;
}

// ── Phase 1: Notebooks, sources, ask, solve, artifacts ──
export function createNotebook(title: string): Promise<Notebook> {
  return post<Notebook>("/notebooks", { title });
}

export function uploadSource(notebookId: string, title: string, text: string, kind = "notes"): Promise<UploadResult> {
  return post<UploadResult>(`/notebooks/${notebookId}/sources/upload`, { title, text, kind });
}

export function askNotebook(notebookId: string, query: string): Promise<AskResponse> {
  return post<AskResponse>(`/notebooks/${notebookId}/ask`, { query });
}

export function solve(content: string, notebookId?: string): Promise<SolveResponse> {
  return post<SolveResponse>("/solve", { input_type: "text", content, notebook_id: notebookId ?? null });
}

export function revealStep(solutionId: string, stepIdx: number): Promise<SolveStep> {
  return post<SolveStep>(`/solve/${solutionId}/reveal`, { step_idx: stepIdx });
}

export function generateArtifact(notebookId: string, artifactType: string): Promise<Artifact> {
  return post<Artifact>(`/notebooks/${notebookId}/artifacts/generate`, { artifact_type: artifactType });
}

// ── Phase 2: Teaching ──
export function startTeaching(notebookId: string): Promise<WhiteboardSession> {
  return post<WhiteboardSession>(`/notebooks/${notebookId}/teaching/start`, {});
}

export function teachingNext(sessionId: string): Promise<WhiteboardSession> {
  return post<WhiteboardSession>(`/teaching/${sessionId}/next`, {});
}

export function teachingPrev(sessionId: string): Promise<WhiteboardSession> {
  return post<WhiteboardSession>(`/teaching/${sessionId}/prev`, {});
}

// ── Phase 2: Quizzes ──
export function generateQuiz(notebookId: string, numQuestions = 5, questionTypes?: string[], topic?: string): Promise<Quiz> {
  return post<Quiz>(`/notebooks/${notebookId}/quizzes/generate`, {
    num_questions: numQuestions,
    question_types: questionTypes,
    topic: topic ?? null,
  });
}

export function getQuizAnswerKey(quizId: string): Promise<AnswerKey> {
  return post<AnswerKey>(`/quizzes/${quizId}/answer-key`, {});
}

export function submitQuizAttempt(quizId: string, answers: { question_id: string; answer: string }[]): Promise<Attempt> {
  return post<Attempt>(`/quizzes/${quizId}/attempt`, { answers });
}

// ── Phase 2: Papers ──
export function generatePaper(notebookId: string, durationMinutes = 60, topic?: string): Promise<QuestionPaper> {
  return post<QuestionPaper>(`/notebooks/${notebookId}/papers/generate`, { duration_minutes: durationMinutes, topic: topic ?? null });
}

export function getPaperAnswerKey(paperId: string): Promise<AnswerKey> {
  return post<AnswerKey>(`/papers/${paperId}/answer-key`, {});
}

export function submitPaperAttempt(paperId: string, answers: { question_id: string; answer: string }[]): Promise<Attempt> {
  return post<Attempt>(`/papers/${paperId}/attempt`, { answers });
}

// ── Phase 2: Reports ──
export function getReport(attemptId: string): Promise<EvalReport> {
  return get<EvalReport>(`/reports/${attemptId}`);
}

// ── Phase 3: Sessions ──
export function startSession(notebookId: string, kind = "study"): Promise<{ id: string }> {
  return post<{ id: string }>(`/notebooks/${notebookId}/sessions/start`, { kind });
}

export function endSession(sessionId: string): Promise<{ id: string; ended_at: string }> {
  return post<{ id: string; ended_at: string }>(`/sessions/${sessionId}/end`, {});
}

// ── Phase 3: Revision ──
export function generateRevisionCards(notebookId: string, topics?: string[], source = "manual"): Promise<{ cards: RevisionCard[] }> {
  return post<{ cards: RevisionCard[] }>(`/notebooks/${notebookId}/revision/generate-cards`, { topics: topics ?? null, source });
}

export function getDueCards(userId = "demo-user"): Promise<{ cards: RevisionCard[] }> {
  return get<{ cards: RevisionCard[] }>(`/revision/due?user_id=${encodeURIComponent(userId)}`);
}

export function reviewCard(cardId: string, correct: boolean): Promise<RevisionCard> {
  return post<RevisionCard>(`/revision/${cardId}/review`, { card_id: cardId, correct });
}

export function getRevisionStats(userId = "demo-user"): Promise<CardStats> {
  return get<CardStats>(`/revision/stats?user_id=${encodeURIComponent(userId)}`);
}

// ── Phase 3: Student mastery ──
export function computeMastery(userId: string, notebookId: string): Promise<KnowledgeState> {
  return post<KnowledgeState>(`/student/${userId}/mastery`, { notebook_id: notebookId });
}

export function getMastery(userId: string, notebookId: string): Promise<KnowledgeState> {
  return get<KnowledgeState>(`/student/${userId}/notebook/${notebookId}/mastery`);
}

export function getWeakTopics(userId: string, notebookId: string): Promise<{ weak_topics: string[] }> {
  return get<{ weak_topics: string[] }>(`/student/${userId}/notebook/${notebookId}/weak-topics`);
}

// ── Phase 3: Analytics ──
export function getNotebookTrends(notebookId: string): Promise<{ trends: TrendPoint[] }> {
  return get<{ trends: TrendPoint[] }>(`/analytics/notebook/${notebookId}/trends`);
}

export function getUserSummary(userId = "demo-user"): Promise<UserSummary> {
  return get<UserSummary>(`/analytics/user/${userId}/summary`);
}

// ── Phase 3: Voice ──
export function textToSpeech(text: string, format = "wav"): Promise<VoiceResult> {
  return post<VoiceResult>("/voice/tts", { text, format });
}

export function speechToText(audioBase64: string, format = "wav"): Promise<VoiceResult> {
  return post<VoiceResult>("/voice/stt", { audio_base64: audioBase64, format });
}
