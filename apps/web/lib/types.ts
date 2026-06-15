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

// ── Phase 4 ──

export type ConnectorType = "website" | "youtube" | "audio" | "google_doc" | "google_slides";
export type PlanTier = "free" | "scholar" | "pro";

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

export interface ImportResult {
  source: { id: string; title: string; kind: string };
  source_guide: SourceGuide;
  import: SourceImport;
}

export interface ImportList {
  imports: SourceImport[];
  supported_types: ConnectorType[];
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

export interface QuotaStatus {
  action: string;
  used: number;
  limit: number | null;
  remaining: number | null;
  allowed: boolean;
}

export interface UsageSummary {
  user_id: string;
  tier: PlanTier;
  status: string;
  billing_period: string;
  provider: string;
  price_cents: number;
  currency: string;
  actions: QuotaStatus[];
}

export interface SubscribeResult {
  subscription: Subscription;
  checkout: { provider: string; status: string; checkout_url: string | null; external_id: string | null; message: string };
  plan: Plan;
}

// ── Phase 5: Auth & observability ──

export type RoleType = "student" | "instructor" | "admin";
export type ShareRole = "viewer" | "editor";

export interface AuthUser {
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

export interface SharedWithItem {
  share_id: string;
  notebook_id: string;
  title: string;
  role: ShareRole;
  owner_id: string;
}

export interface AuthResult {
  user: AuthUser;
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
