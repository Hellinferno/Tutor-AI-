export type ArtifactType = "summary_notes" | "study_guide" | "planner" | "timetable" | "revision_cards";
export type GroundingState = "from_sources" | "general_knowledge" | "insufficient_source_support";
export type VerifyMethod = "code_exec" | "symbolic" | "formula" | "self_consistency" | "cross_model" | "unverified";
export type QuestionType = "mcq" | "true_false" | "short_answer";
export type AttemptSourceType = "quiz" | "paper";
export type Difficulty = "easy" | "medium" | "hard";

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

export interface AskResponse {
  answer: string;
  grounding: GroundingState;
  citations: Citation[];
  suggested_followups: string[];
}

export interface SolveResponse {
  question_id: string;
  solution_id: string;
  answer: string;
  steps: Array<{ idx: number; text: string; revealed: boolean }>;
  verified: boolean;
  verify_method: VerifyMethod;
  from_cache: boolean;
  citations: Citation[];
  latency_ms: number;
}

export interface Artifact {
  id: string;
  notebook_id: string;
  artifact_type: ArtifactType;
  title: string;
  content_markdown: string;
  citations: Citation[];
  created_at: string;
}

export interface WhiteboardConcept {
  name: string;
  explanation: string;
  citations: Citation[];
  whiteboard: Array<Record<string, string>>;
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
  difficulty: Difficulty;
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

export interface AnswerKey {
  id: string;
  source_id: string;
  source_type: AttemptSourceType;
  answers: Array<Record<string, unknown>>;
  verified: boolean;
  verification_method: string;
}

export interface Attempt {
  id: string;
  source_id: string;
  source_type: AttemptSourceType;
  user_id: string;
  answers: Array<Record<string, unknown>>;
  total_score: number;
  max_score: number;
  completed_at: string;
}

export interface EvalReport {
  id: string;
  attempt_id: string;
  total_score: number;
  max_score: number;
  percentage: number;
  per_question: Array<Record<string, unknown>>;
  weak_topics: string[];
  strong_topics: string[];
  summary: string;
}
