export type ArtifactType = "summary_notes" | "study_guide" | "planner" | "timetable" | "revision_cards";
export type GroundingState = "from_sources" | "general_knowledge" | "insufficient_source_support";
export type VerifyMethod = "code_exec" | "symbolic" | "formula" | "self_consistency" | "cross_model" | "unverified";
export type QuestionType = "mcq" | "true_false" | "short_answer";
export type AttemptSourceType = "quiz" | "paper";
export type Difficulty = "easy" | "medium" | "hard";
export type ConnectorType = "website" | "youtube" | "audio" | "google_doc" | "google_slides";
export type PlanTier = "free" | "scholar" | "pro";
export type MeteredAction =
  | "ask"
  | "solve"
  | "quiz"
  | "paper"
  | "artifact"
  | "source_import"
  | "teaching";

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

// ── Phase 4: connectors, multi-agent teaching, pricing ──

export interface SourceImport {
  id: string;
  notebook_id: string;
  source_id: string;
  connector_type: ConnectorType;
  title: string;
  status: string;
  metadata: Record<string, unknown>;
  warnings: string[];
  created_at: string;
}

export interface AgentTurn {
  agent_id: string;
  role: string;
  concept_index: number;
  title: string;
  content: string;
  citations: Citation[];
  confidence: number;
}

export interface MultiAgentTeachingSession {
  id: string;
  notebook_id: string;
  current_concept_idx: number;
  concepts: WhiteboardConcept[];
  agent_turns: AgentTurn[];
  completed: boolean;
}

export interface Plan {
  tier: PlanTier;
  name: string;
  price_cents: number;
  currency: string;
  quotas: Record<string, number | null>;
  features: string[];
}

export interface Subscription {
  id: string;
  user_id: string;
  tier: PlanTier;
  status: string;
  billing_period: string;
  provider: string;
  external_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UsageRecord {
  id: string;
  user_id: string;
  action: MeteredAction;
  billing_period: string;
  quantity: number;
  created_at: string;
}

// ── Phase 5: auth & observability ──

export type RoleType = "student" | "instructor" | "admin";
export type ShareRole = "viewer" | "editor";

export interface User {
  id: string;
  email: string;
  subject_domain: string;
  role: RoleType;
  prefs: Record<string, unknown>;
  created_at: string;
}

export interface NotebookShare {
  id: string;
  notebook_id: string;
  owner_id: string;
  shared_with_id: string;
  shared_with_email: string;
  role: ShareRole;
  created_at: string;
}

export interface AuthResult {
  user: User;
  token: string;
  token_type: string;
}

export interface MetricsSnapshot {
  asks: number;
  weak_retrieval_refusal_rate: number;
  citation_coverage_rate: number;
  solves: number;
  verified_rate: number;
  false_verified_rate: number;
  cache_hit_rate: number;
  solve_latency_ms: { p50: number; p90: number; p99: number };
  notion_export_success_rate: number;
}

// ── Phase 8: classrooms, assignments, class analytics ──

export type AssignmentKind = "quiz" | "paper";

export interface Class {
  id: string;
  instructor_id: string;
  name: string;
  code: string;
  created_at: string;
}

export interface ClassEnrollment {
  id: string;
  class_id: string;
  student_id: string;
  joined_at: string;
}

export interface Assignment {
  id: string;
  class_id: string;
  kind: AssignmentKind;
  source_id: string;
  title: string;
  due_at: string | null;
  created_at: string;
}

export interface AssignmentSubmission {
  id: string;
  assignment_id: string;
  student_id: string;
  attempt_id: string;
  submitted_at: string;
}
