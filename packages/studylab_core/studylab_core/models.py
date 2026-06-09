from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


ArtifactType = Literal["summary_notes", "study_guide", "planner", "timetable", "revision_cards"]
GroundingState = Literal["from_sources", "general_knowledge", "insufficient_source_support"]
VerifyMethod = Literal["code_exec", "symbolic", "formula", "self_consistency", "cross_model", "unverified"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
