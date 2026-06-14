from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


ArtifactType = Literal["summary_notes", "study_guide", "planner", "timetable", "revision_cards"]
GroundingState = Literal["from_sources", "general_knowledge", "insufficient_source_support"]
VerifyMethod = Literal["code_exec", "symbolic", "formula", "self_consistency", "cross_model", "unverified"]
ConnectorType = Literal["website", "youtube", "audio", "google_doc", "google_slides"]

QuestionType = Literal["mcq", "true_false", "short_answer"]
AttemptSourceType = Literal["quiz", "paper"]
Difficulty = Literal["easy", "medium", "hard"]
PlanTier = Literal["free", "scholar", "pro"]
MeteredAction = Literal["ask", "solve", "quiz", "paper", "artifact", "source_import", "teaching"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    subject_domain: str = "ai_ds"  # ai_ds, analytics, finance
    prefs: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass
class Notebook:
    id: str
    title: str
    user_id: str = "demo-user"
    created_at: str = field(default_factory=utc_now)


@dataclass
class Source:
    id: str
    notebook_id: str
    title: str
    kind: str
    text: str
    status: str = "ready"
    created_at: str = field(default_factory=utc_now)


@dataclass
class SourceChunk:
    id: str
    source_id: str
    notebook_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    vector_id: str


@dataclass
class SourceGuide:
    source_id: str
    summary: str
    key_concepts: list[str]
    suggested_questions: list[str]


@dataclass
class SourceImport:
    id: str
    notebook_id: str
    source_id: str
    connector_type: ConnectorType
    title: str
    status: str
    metadata: dict[str, Any]
    warnings: list[str]
    created_at: str = field(default_factory=utc_now)


@dataclass
class Citation:
    source_id: str
    source_title: str
    chunk_index: int
    start_char: int
    end_char: int
    snippet: str
    score: float


@dataclass
class AskResponse:
    answer: str
    grounding: GroundingState
    citations: list[Citation]
    suggested_followups: list[str]


@dataclass
class Solution:
    id: str
    question_id: str
    question_hash: str
    answer: str
    steps: list[dict[str, Any]]
    verified: bool
    verify_method: VerifyMethod
    citations: list[Citation]
    created_at: str = field(default_factory=utc_now)


@dataclass
class SolveResponse:
    question_id: str
    solution_id: str
    answer: str
    steps: list[dict[str, Any]]
    verified: bool
    verify_method: VerifyMethod
    from_cache: bool
    citations: list[Citation]
    latency_ms: int


@dataclass
class Artifact:
    id: str
    notebook_id: str
    artifact_type: ArtifactType
    title: str
    content_markdown: str
    citations: list[Citation]
    created_at: str = field(default_factory=utc_now)


@dataclass
class NotionExportResult:
    connected: bool
    message: str
    page_url: str | None = None
    page_id: str | None = None


# ── Phase 2: Teaching, Quizzes, Papers, Eval ──────────────────────────────

@dataclass
class WhiteboardConcept:
    name: str
    explanation: str
    citations: list[Citation]
    whiteboard: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WhiteboardSession:
    id: str
    notebook_id: str
    current_concept_idx: int
    concepts: list[WhiteboardConcept]
    completed: bool = False


@dataclass
class AgentTurn:
    agent_id: str
    role: str
    concept_index: int
    title: str
    content: str
    citations: list[Citation]
    confidence: float


@dataclass
class MultiAgentTeachingSession:
    id: str
    notebook_id: str
    current_concept_idx: int
    concepts: list[WhiteboardConcept]
    agent_turns: list[AgentTurn]
    completed: bool = False


@dataclass
class QuizQuestion:
    id: str
    type: QuestionType
    question_text: str
    correct_answer: str
    points: int
    difficulty: Difficulty = "medium"
    options: list[str] | None = None
    citations: list[Citation] | None = None


@dataclass
class Quiz:
    id: str
    notebook_id: str
    title: str
    questions: list[QuizQuestion]
    topic: str | None = None


@dataclass
class PaperSection:
    title: str
    instructions: str
    questions: list[QuizQuestion]


@dataclass
class QuestionPaper:
    id: str
    notebook_id: str
    title: str
    sections: list[PaperSection]
    total_marks: int
    duration_minutes: int


@dataclass
class Attempt:
    id: str
    source_id: str
    source_type: AttemptSourceType
    user_id: str
    answers: list[dict]
    total_score: float
    max_score: float
    completed_at: str = field(default_factory=utc_now)


@dataclass
class AnswerKey:
    id: str
    source_id: str
    source_type: AttemptSourceType
    answers: list[dict]
    verified: bool = True
    verification_method: str = "deterministic_source_check"


@dataclass
class EvalReport:
    id: str
    attempt_id: str
    total_score: float
    max_score: float
    percentage: float
    per_question: list[dict]
    weak_topics: list[str]
    strong_topics: list[str]
    summary: str


# ── Phase 3: Memory, Revision, Analytics, Voice ──────────────────────────

@dataclass
class RevisionCard:
    id: str
    user_id: str
    notebook_id: str
    topic: str
    due_date: str
    interval_days: int
    state: str = "queued"  # queued, done, lapsed
    easiness_factor: float = 2.5
    correct_streak: int = 0
    source: str = "manual"  # manual, eval_weak_topic


@dataclass
class Session:
    id: str
    user_id: str
    notebook_id: str
    kind: str = "study"  # study, quiz, paper, revision
    started_at: str = field(default_factory=utc_now)
    ended_at: str | None = None
    interactions: list[dict] = field(default_factory=list)


@dataclass
class StudentProfile:
    id: str
    user_id: str
    notebook_id: str
    updated_at: str = field(default_factory=utc_now)


@dataclass
class TopicMastery:
    id: str
    student_profile_id: str
    topic: str
    score: float
    attempt_count: int
    last_attempt_date: str | None = None


@dataclass
class KnowledgeState:
    user_id: str
    notebook_id: str
    masteries: list[TopicMastery]
    overall_score: float
    weak_topics: list[str]
    strong_topics: list[str]


@dataclass
class VoiceResult:
    ok: bool
    text: str
    format: str = ""
    audio_base64: str = ""
    error: str = ""


# ── Phase 4: Pricing & economics, connectors, multi-agent teaching ────────

@dataclass
class Plan:
    """A purchasable plan tier with deterministic monthly action quotas.

    A quota of ``None`` means unlimited. Prices are stored in integer cents to
    avoid floating-point money bugs.
    """

    tier: PlanTier
    name: str
    price_cents: int
    currency: str
    quotas: dict[str, int | None]
    features: list[str]


@dataclass
class Subscription:
    id: str
    user_id: str
    tier: PlanTier
    status: str  # active, canceled, past_due
    billing_period: str  # YYYY-MM, the period usage is metered against
    provider: str  # mock, stripe
    external_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class UsageRecord:
    id: str
    user_id: str
    action: MeteredAction
    billing_period: str  # YYYY-MM
    quantity: int = 1
    created_at: str = field(default_factory=utc_now)
