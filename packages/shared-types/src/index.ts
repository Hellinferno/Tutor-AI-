export type ArtifactType = "summary_notes" | "study_guide" | "planner" | "timetable" | "revision_cards";
export type GroundingState = "from_sources" | "general_knowledge" | "insufficient_source_support";
export type VerifyMethod = "code_exec" | "symbolic" | "formula" | "self_consistency" | "cross_model" | "unverified";

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
