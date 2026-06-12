// Response shapes returned by the gateway. These mirror the Python dataclasses in
// packages/studylab_core/studylab_core/models.py and the package @studylab/shared-types.

export type GroundingState = "from_sources" | "general_knowledge" | "insufficient_source_support";
export type VerifyMethod = "code_exec" | "symbolic" | "formula" | "self_consistency" | "cross_model" | "unverified";
export type QuestionType = "mcq" | "true_false" | "short_answer";
export type AttemptSourceType = "quiz" | "paper";

export interface Citation {
  source_id: string;
  source_title: string;
  chunk_index: number;
  start_char: number;
  end_char: number;
  snippet: string;
  score: number;
}

export interface Notebook {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
}

export interface SourceGuide {
  source_id: string;
  summary: string;
  key_concepts: string[];
  suggested_questions: string[];
}

export interface UploadResult {
  source: { id: string; title: string; kind: string };
  source_guide: SourceGuide;
}

export interface AskResponse {
  answer: string;
  grounding: GroundingState;
  citations: Citation[];
  suggested_followups: string[];
}

export interface SolveStep {
  idx: number;
  text: string;
  revealed: boolean;
}

export interface SolveResponse {
  question_id: string;
  solution_id: string;
  answer: string;
  steps: SolveStep[];
  verified: boolean;
  verify_method: VerifyMethod;
  from_cache: boolean;
  citations: Citation[];
  latency_ms: number;
}

export interface WhiteboardElement {
  type: string;
  text?: string;
  katex?: string;
  lang?: string;
}

export interface WhiteboardConcept {
  name: string;
  explanation: string;
  citations: Citation[];
  whiteboard: WhiteboardElement[];
}

export interface WhiteboardSession {
  id: string;
  notebook_id: string;
  current_concept_idx: number;
  concepts: WhiteboardConcept[];
  completed: boolean;
}

export interface QuizQuestion {
  id: string;
  type: QuestionType;
  question_text: string;
  correct_answer: string;
  points: number;
  difficulty: string;
  options?: string[] | null;
  citations?: Citation[] | null;
}

export interface Quiz {
  id: string;
  notebook_id: string;
  title: string;
  questions: QuizQuestion[];
  topic?: string | null;
}

export interface AnswerKeyEntry {
  question_id: string;
  correct_answer: string;
  verified: boolean;
  verification_method: string;
  [k: string]: unknown;
}

export interface AnswerKey {
  id: string;
  source_id: string;
  source_type: AttemptSourceType;
  answers: AnswerKeyEntry[];
  verified: boolean;
  verification_method: string;
}

export interface ScoredAnswer {
  question_id: string;
  given_answer: string;
  correct: boolean;
  score: number;
  max_score: number;
  feedback: string;
}

export interface Attempt {
  id: string;
  source_id: string;
  source_type: AttemptSourceType;
  user_id: string;
  answers: ScoredAnswer[];
  total_score: number;
  max_score: number;
  completed_at: string;
}

export interface PaperSection {
  title: string;
  instructions: string;
  questions: QuizQuestion[];
}

export interface QuestionPaper {
  id: string;
  notebook_id: string;
  title: string;
  sections: PaperSection[];
  total_marks: number;
  duration_minutes: number;
}

export interface EvalReport {
  id: string;
  attempt_id: string;
  total_score: number;
  max_score: number;
  percentage: number;
  per_question: ScoredAnswer[];
  weak_topics: string[];
  strong_topics: string[];
  summary: string;
}

export interface Artifact {
  id: string;
  notebook_id: string;
  artifact_type: string;
  title: string;
  content_markdown: string;
  citations: Citation[];
  created_at: string;
}

// ── Phase 3 ──

export interface RevisionCard {
  id: string;
  user_id: string;
  notebook_id: string;
  topic: string;
  due_date: string;
  interval_days: number;
  state: string;
  easiness_factor: number;
  correct_streak: number;
  source: string;
}

export interface CardStats {
  total: number;
  due: number;
  done: number;
  lapsed: number;
  avg_easiness: number;
}

export interface TopicMastery {
  id: string;
  student_profile_id: string;
  topic: string;
  score: number;
  attempt_count: number;
  last_attempt_date?: string | null;
}

export interface KnowledgeState {
  user_id: string;
  notebook_id: string;
  masteries: TopicMastery[];
  overall_score: number;
  weak_topics: string[];
  strong_topics: string[];
}

export interface TrendPoint {
  attempt_id: string;
  score: number;
  max_score: number;
  weak_topics: string[];
  strong_topics: string[];
}

export interface UserSummary {
  user_id: string;
  total_attempts: number;
  avg_score: number;
  top_weak_topics: string[];
  top_strong_topics: string[];
  total_time_minutes: number;
}

export interface VoiceResult {
  ok: boolean;
  text: string;
  format: string;
  audio_base64: string;
  error: string;
}
