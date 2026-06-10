from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Callable
from uuid import uuid4

from .models import (
    AnswerKey,
    Artifact,
    Attempt,
    Citation,
    EvalReport,
    Notebook,
    QuestionPaper,
    Quiz,
    QuizQuestion,
    Solution,
    Source,
    SourceChunk,
    SourceGuide,
    WhiteboardSession,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS notebooks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  user_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL,
  title TEXT NOT NULL,
  kind TEXT NOT NULL,
  text TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_chunks (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  notebook_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  start_char INTEGER NOT NULL,
  end_char INTEGER NOT NULL,
  vector_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_guides (
  source_id TEXT PRIMARY KEY,
  summary TEXT NOT NULL,
  key_concepts TEXT NOT NULL,
  suggested_questions TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS solutions (
  id TEXT PRIMARY KEY,
  question_id TEXT NOT NULL,
  question_hash TEXT NOT NULL,
  answer TEXT NOT NULL,
  steps TEXT NOT NULL,
  verified INTEGER NOT NULL,
  verify_method TEXT NOT NULL,
  citations TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  title TEXT NOT NULL,
  content_markdown TEXT NOT NULL,
  citations TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS whiteboard_sessions (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL,
  current_concept_idx INTEGER NOT NULL,
  concepts TEXT NOT NULL,
  completed INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS quizzes (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL,
  title TEXT NOT NULL,
  topic TEXT,
  questions TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS question_papers (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL,
  title TEXT NOT NULL,
  sections TEXT NOT NULL,
  total_marks INTEGER NOT NULL,
  duration_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  user_id TEXT NOT NULL,
  answers TEXT NOT NULL,
  total_score REAL NOT NULL,
  max_score REAL NOT NULL,
  completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS answer_keys (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  answers TEXT NOT NULL,
  verified INTEGER NOT NULL DEFAULT 1,
  verification_method TEXT NOT NULL DEFAULT 'deterministic_source_check'
);
CREATE TABLE IF NOT EXISTS eval_reports (
  id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL,
  total_score REAL NOT NULL,
  max_score REAL NOT NULL,
  percentage REAL NOT NULL,
  per_question TEXT NOT NULL,
  weak_topics TEXT NOT NULL,
  strong_topics TEXT NOT NULL,
  summary TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_notebook ON source_chunks (notebook_id);
CREATE INDEX IF NOT EXISTS idx_solutions_hash ON solutions (question_hash, created_at);
"""


def _citations_to_json(citations: list[Citation]) -> str:
    return json.dumps([asdict(citation) for citation in citations])


def _citations_from_json(raw: str) -> list[Citation]:
    return [Citation(**item) for item in json.loads(raw)]


class _TableView:
    """Read-only dict-like view over a SQLite table.

    Mirrors the attribute access (``store.chunks.values()``, ``store.guides.get()``,
    ``store.artifacts[id]``) that callers used against ``InMemoryStudyLabStore`` so the
    two stores are interchangeable without touching call sites.
    """

    def __init__(self, load_all: Callable[[], dict[str, Any]], load_one: Callable[[str], Any]) -> None:
        self._load_all = load_all
        self._load_one = load_one

    def values(self):  # noqa: ANN201 - matches dict.values surface
        return list(self._load_all().values())

    def items(self):  # noqa: ANN201 - matches dict.items surface
        return list(self._load_all().items())

    def keys(self):  # noqa: ANN201 - matches dict.keys surface
        return list(self._load_all().keys())

    def get(self, key: str, default: Any = None) -> Any:
        value = self._load_one(key)
        return value if value is not None else default

    def __getitem__(self, key: str) -> Any:
        value = self._load_one(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        return self._load_one(key) is not None

    def __iter__(self):  # noqa: ANN204 - matches dict iteration
        return iter(self._load_all())


class SqliteStudyLabStore:
    """Durable SQLite-backed store with the same surface as InMemoryStudyLabStore.

    This is the persistent path: data survives process restarts. Postgres remains the
    intended production target (see packages/db/migrations); this keeps the SQL contract
    explicit and verifiable locally without a database server.
    """

    def __init__(self, path: str = "studylab.db") -> None:
        self.path = path
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._ensure_compat_columns()
            self._conn.commit()

        self.notebooks = _TableView(self._all_notebooks, self._get_notebook)
        self.sources = _TableView(self._all_sources, self._get_source)
        self.chunks = _TableView(self._all_chunks, self._get_chunk)
        self.guides = _TableView(self._all_guides, self.get_guide)
        self.solutions = _TableView(self._all_solutions, self._get_solution)
        self.artifacts = _TableView(self._all_artifacts, self._get_artifact)
        self.whiteboard_sessions = _TableView(self._all_whiteboard_sessions, self._get_whiteboard_session)
        self.quizzes = _TableView(self._all_quizzes, self._get_quiz)
        self.question_papers = _TableView(self._all_question_papers, self._get_question_paper)
        self.attempts = _TableView(self._all_attempts, self._get_attempt)
        self.answer_keys = _TableView(self._all_answer_keys, self._get_answer_key)
        self.eval_reports = _TableView(self._all_eval_reports, self._get_eval_report)

    def _ensure_compat_columns(self) -> None:
        columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(answer_keys)").fetchall()}
        if "verified" not in columns:
            self._conn.execute("ALTER TABLE answer_keys ADD COLUMN verified INTEGER NOT NULL DEFAULT 1")
        if "verification_method" not in columns:
            self._conn.execute(
                "ALTER TABLE answer_keys ADD COLUMN verification_method TEXT NOT NULL DEFAULT 'deterministic_source_check'"
            )

    # -- identity & serialization -------------------------------------------------

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    def to_plain(self, value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, list):
            return [self.to_plain(item) for item in value]
        if isinstance(value, dict):
            return {key: self.to_plain(item) for key, item in value.items()}
        return value

    # -- writes -------------------------------------------------------------------

    def add_notebook(self, title: str, user_id: str = "demo-user") -> Notebook:
        notebook = Notebook(id=self.next_id("notebook"), title=title, user_id=user_id)
        with self._lock:
            self._conn.execute(
                "INSERT INTO notebooks (id, title, user_id, created_at) VALUES (?, ?, ?, ?)",
                (notebook.id, notebook.title, notebook.user_id, notebook.created_at),
            )
            self._conn.commit()
        return notebook

    def add_source(self, notebook_id: str, title: str, kind: str, text: str) -> Source:
        self.require_notebook(notebook_id)
        source = Source(id=self.next_id("source"), notebook_id=notebook_id, title=title, kind=kind, text=text)
        with self._lock:
            self._conn.execute(
                "INSERT INTO sources (id, notebook_id, title, kind, text, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (source.id, source.notebook_id, source.title, source.kind, source.text, source.status, source.created_at),
            )
            self._conn.commit()
        return source

    def add_chunk(
        self,
        source_id: str,
        notebook_id: str,
        chunk_index: int,
        text: str,
        start_char: int,
        end_char: int,
    ) -> SourceChunk:
        chunk = SourceChunk(
            id=self.next_id("chunk"),
            source_id=source_id,
            notebook_id=notebook_id,
            chunk_index=chunk_index,
            text=text,
            start_char=start_char,
            end_char=end_char,
            vector_id=f"local:{source_id}:{chunk_index}",
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO source_chunks (id, source_id, notebook_id, chunk_index, text, start_char, end_char, vector_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    chunk.id,
                    chunk.source_id,
                    chunk.notebook_id,
                    chunk.chunk_index,
                    chunk.text,
                    chunk.start_char,
                    chunk.end_char,
                    chunk.vector_id,
                ),
            )
            self._conn.commit()
        return chunk

    def set_guide(self, guide: SourceGuide) -> SourceGuide:
        with self._lock:
            self._conn.execute(
                "INSERT INTO source_guides (source_id, summary, key_concepts, suggested_questions) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(source_id) DO UPDATE SET summary=excluded.summary, "
                "key_concepts=excluded.key_concepts, suggested_questions=excluded.suggested_questions",
                (guide.source_id, guide.summary, json.dumps(guide.key_concepts), json.dumps(guide.suggested_questions)),
            )
            self._conn.commit()
        return guide

    def add_solution(self, solution: Solution) -> Solution:
        with self._lock:
            self._conn.execute(
                "INSERT INTO solutions (id, question_id, question_hash, answer, steps, verified, verify_method, citations, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    solution.id,
                    solution.question_id,
                    solution.question_hash,
                    solution.answer,
                    json.dumps(solution.steps),
                    int(solution.verified),
                    solution.verify_method,
                    _citations_to_json(solution.citations),
                    solution.created_at,
                ),
            )
            self._conn.commit()
        return solution

    def save_solution(self, solution: Solution) -> Solution:
        """Persist mutations to an existing solution (e.g. a revealed step)."""
        with self._lock:
            self._conn.execute(
                "UPDATE solutions SET answer=?, steps=?, verified=?, verify_method=?, citations=? WHERE id=?",
                (
                    solution.answer,
                    json.dumps(solution.steps),
                    int(solution.verified),
                    solution.verify_method,
                    _citations_to_json(solution.citations),
                    solution.id,
                ),
            )
            self._conn.commit()
        return solution

    def add_artifact(self, artifact: Artifact) -> Artifact:
        with self._lock:
            self._conn.execute(
                "INSERT INTO artifacts (id, notebook_id, artifact_type, title, content_markdown, citations, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    artifact.id,
                    artifact.notebook_id,
                    artifact.artifact_type,
                    artifact.title,
                    artifact.content_markdown,
                    _citations_to_json(artifact.citations),
                    artifact.created_at,
                ),
            )
            self._conn.commit()
        return artifact

    # ── Phase 2 writes ─────────────────────────────────────────────────────

    def add_whiteboard_session(self, session: WhiteboardSession) -> WhiteboardSession:
        with self._lock:
            self._conn.execute(
                "INSERT INTO whiteboard_sessions (id, notebook_id, current_concept_idx, concepts, completed) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session.id,
                    session.notebook_id,
                    session.current_concept_idx,
                    json.dumps([asdict(c) for c in session.concepts]),
                    int(session.completed),
                ),
            )
            self._conn.commit()
        return session

    def save_whiteboard_session(self, session: WhiteboardSession) -> WhiteboardSession:
        with self._lock:
            self._conn.execute(
                "UPDATE whiteboard_sessions SET current_concept_idx=?, concepts=?, completed=? WHERE id=?",
                (
                    session.current_concept_idx,
                    json.dumps([asdict(c) for c in session.concepts]),
                    int(session.completed),
                    session.id,
                ),
            )
            self._conn.commit()
        return session

    def add_quiz(self, quiz: Quiz) -> Quiz:
        with self._lock:
            self._conn.execute(
                "INSERT INTO quizzes (id, notebook_id, title, topic, questions) VALUES (?, ?, ?, ?, ?)",
                (quiz.id, quiz.notebook_id, quiz.title, quiz.topic, json.dumps([asdict(q) for q in quiz.questions])),
            )
            self._conn.commit()
        return quiz

    def add_question_paper(self, paper: QuestionPaper) -> QuestionPaper:
        with self._lock:
            self._conn.execute(
                "INSERT INTO question_papers (id, notebook_id, title, sections, total_marks, duration_minutes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    paper.id,
                    paper.notebook_id,
                    paper.title,
                    json.dumps([asdict(s) for s in paper.sections]),
                    paper.total_marks,
                    paper.duration_minutes,
                ),
            )
            self._conn.commit()
        return paper

    def add_attempt(self, attempt: Attempt) -> Attempt:
        with self._lock:
            self._conn.execute(
                "INSERT INTO attempts (id, source_id, source_type, user_id, answers, total_score, max_score, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt.id,
                    attempt.source_id,
                    attempt.source_type,
                    attempt.user_id,
                    json.dumps(attempt.answers),
                    attempt.total_score,
                    attempt.max_score,
                    attempt.completed_at,
                ),
            )
            self._conn.commit()
        return attempt

    def add_answer_key(self, key: AnswerKey) -> AnswerKey:
        with self._lock:
            self._conn.execute(
                "INSERT INTO answer_keys (id, source_id, source_type, answers, verified, verification_method) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    key.id,
                    key.source_id,
                    key.source_type,
                    json.dumps(key.answers),
                    1 if key.verified else 0,
                    key.verification_method,
                ),
            )
            self._conn.commit()
        return key

    def add_eval_report(self, report: EvalReport) -> EvalReport:
        with self._lock:
            self._conn.execute(
                "INSERT INTO eval_reports (id, attempt_id, total_score, max_score, percentage, per_question, weak_topics, strong_topics, summary) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    report.id,
                    report.attempt_id,
                    report.total_score,
                    report.max_score,
                    report.percentage,
                    json.dumps(report.per_question),
                    json.dumps(report.weak_topics),
                    json.dumps(report.strong_topics),
                    report.summary,
                ),
            )
            self._conn.commit()
        return report

    # -- Phase 2 reads -----------------------------------------------------------

    def require_whiteboard_session(self, session_id: str) -> WhiteboardSession:
        session = self._get_whiteboard_session(session_id)
        if session is None:
            raise KeyError(f"Whiteboard session not found: {session_id}")
        return session

    def require_quiz(self, quiz_id: str) -> Quiz:
        quiz = self._get_quiz(quiz_id)
        if quiz is None:
            raise KeyError(f"Quiz not found: {quiz_id}")
        return quiz

    def require_question_paper(self, paper_id: str) -> QuestionPaper:
        paper = self._get_question_paper(paper_id)
        if paper is None:
            raise KeyError(f"Question paper not found: {paper_id}")
        return paper

    def require_attempt(self, attempt_id: str) -> Attempt:
        attempt = self._get_attempt(attempt_id)
        if attempt is None:
            raise KeyError(f"Attempt not found: {attempt_id}")
        return attempt

    def require_answer_key(self, key_id: str) -> AnswerKey:
        key = self._get_answer_key(key_id)
        if key is None:
            raise KeyError(f"Answer key not found: {key_id}")
        return key

    def require_eval_report(self, report_id: str) -> EvalReport:
        report = self._get_eval_report(report_id)
        if report is None:
            raise KeyError(f"Eval report not found: {report_id}")
        return report

    # -- reads --------------------------------------------------------------------

    def get_cached_solution(self, question_hash: str) -> Solution | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM solutions WHERE question_hash=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (question_hash,),
            ).fetchone()
        return self._row_to_solution(row) if row else None

    def require_notebook(self, notebook_id: str) -> Notebook:
        notebook = self._get_notebook(notebook_id)
        if notebook is None:
            raise KeyError(f"Notebook not found: {notebook_id}")
        return notebook

    def require_source(self, source_id: str) -> Source:
        source = self._get_source(source_id)
        if source is None:
            raise KeyError(f"Source not found: {source_id}")
        return source

    def require_solution(self, solution_id: str) -> Solution:
        solution = self._get_solution(solution_id)
        if solution is None:
            raise KeyError(f"Solution not found: {solution_id}")
        return solution

    def get_guide(self, source_id: str) -> SourceGuide | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM source_guides WHERE source_id=?", (source_id,)).fetchone()
        return self._row_to_guide(row) if row else None

    def notebook_chunks(self, notebook_id: str) -> list[SourceChunk]:
        self.require_notebook(notebook_id)
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM source_chunks WHERE notebook_id=? ORDER BY source_id, chunk_index",
                (notebook_id,),
            ).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def notebook_guides(self, notebook_id: str) -> list[SourceGuide]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT g.* FROM source_guides g JOIN sources s ON s.id = g.source_id WHERE s.notebook_id=?",
                (notebook_id,),
            ).fetchall()
        return [self._row_to_guide(row) for row in rows]

    # -- row mappers --------------------------------------------------------------

    def _row_to_notebook(self, row: sqlite3.Row) -> Notebook:
        return Notebook(id=row["id"], title=row["title"], user_id=row["user_id"], created_at=row["created_at"])

    def _row_to_source(self, row: sqlite3.Row) -> Source:
        return Source(
            id=row["id"],
            notebook_id=row["notebook_id"],
            title=row["title"],
            kind=row["kind"],
            text=row["text"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def _row_to_chunk(self, row: sqlite3.Row) -> SourceChunk:
        return SourceChunk(
            id=row["id"],
            source_id=row["source_id"],
            notebook_id=row["notebook_id"],
            chunk_index=row["chunk_index"],
            text=row["text"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            vector_id=row["vector_id"],
        )

    def _row_to_guide(self, row: sqlite3.Row) -> SourceGuide:
        return SourceGuide(
            source_id=row["source_id"],
            summary=row["summary"],
            key_concepts=json.loads(row["key_concepts"]),
            suggested_questions=json.loads(row["suggested_questions"]),
        )

    def _row_to_solution(self, row: sqlite3.Row) -> Solution:
        return Solution(
            id=row["id"],
            question_id=row["question_id"],
            question_hash=row["question_hash"],
            answer=row["answer"],
            steps=json.loads(row["steps"]),
            verified=bool(row["verified"]),
            verify_method=row["verify_method"],
            citations=_citations_from_json(row["citations"]),
            created_at=row["created_at"],
        )

    def _row_to_artifact(self, row: sqlite3.Row) -> Artifact:
        return Artifact(
            id=row["id"],
            notebook_id=row["notebook_id"],
            artifact_type=row["artifact_type"],
            title=row["title"],
            content_markdown=row["content_markdown"],
            citations=_citations_from_json(row["citations"]),
            created_at=row["created_at"],
        )

    # ── Phase 2 row mappers ──────────────────────────────────────────────

    def _row_to_whiteboard_session(self, row: sqlite3.Row) -> WhiteboardSession:
        from .models import WhiteboardConcept

        concepts_data = json.loads(row["concepts"])
        concepts = [WhiteboardConcept(**c) for c in concepts_data]
        return WhiteboardSession(
            id=row["id"],
            notebook_id=row["notebook_id"],
            current_concept_idx=row["current_concept_idx"],
            concepts=concepts,
            completed=bool(row["completed"]),
        )

    def _row_to_quiz(self, row: sqlite3.Row) -> Quiz:
        questions_data = json.loads(row["questions"])
        questions = [QuizQuestion(**q) for q in questions_data]
        return Quiz(
            id=row["id"],
            notebook_id=row["notebook_id"],
            title=row["title"],
            topic=row["topic"],
            questions=questions,
        )

    def _row_to_question_paper(self, row: sqlite3.Row) -> QuestionPaper:
        from .models import PaperSection

        sections_data = json.loads(row["sections"])
        sections = []
        for s in sections_data:
            questions = [QuizQuestion(**q) for q in s["questions"]]
            sections.append(PaperSection(title=s["title"], instructions=s["instructions"], questions=questions))
        return QuestionPaper(
            id=row["id"],
            notebook_id=row["notebook_id"],
            title=row["title"],
            sections=sections,
            total_marks=row["total_marks"],
            duration_minutes=row["duration_minutes"],
        )

    def _row_to_attempt(self, row: sqlite3.Row) -> Attempt:
        return Attempt(
            id=row["id"],
            source_id=row["source_id"],
            source_type=row["source_type"],
            user_id=row["user_id"],
            answers=json.loads(row["answers"]),
            total_score=row["total_score"],
            max_score=row["max_score"],
            completed_at=row["completed_at"],
        )

    def _row_to_answer_key(self, row: sqlite3.Row) -> AnswerKey:
        return AnswerKey(
            id=row["id"],
            source_id=row["source_id"],
            source_type=row["source_type"],
            answers=json.loads(row["answers"]),
            verified=bool(row["verified"]),
            verification_method=row["verification_method"],
        )

    def _row_to_eval_report(self, row: sqlite3.Row) -> EvalReport:
        return EvalReport(
            id=row["id"],
            attempt_id=row["attempt_id"],
            total_score=row["total_score"],
            max_score=row["max_score"],
            percentage=row["percentage"],
            per_question=json.loads(row["per_question"]),
            weak_topics=json.loads(row["weak_topics"]),
            strong_topics=json.loads(row["strong_topics"]),
            summary=row["summary"],
        )

    # -- single/all loaders backing the table views -------------------------------

    def _get_notebook(self, key: str) -> Notebook | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM notebooks WHERE id=?", (key,)).fetchone()
        return self._row_to_notebook(row) if row else None

    def _get_source(self, key: str) -> Source | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM sources WHERE id=?", (key,)).fetchone()
        return self._row_to_source(row) if row else None

    def _get_chunk(self, key: str) -> SourceChunk | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM source_chunks WHERE id=?", (key,)).fetchone()
        return self._row_to_chunk(row) if row else None

    def _get_solution(self, key: str) -> Solution | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM solutions WHERE id=?", (key,)).fetchone()
        return self._row_to_solution(row) if row else None

    def _get_artifact(self, key: str) -> Artifact | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM artifacts WHERE id=?", (key,)).fetchone()
        return self._row_to_artifact(row) if row else None

    def _all_notebooks(self) -> dict[str, Notebook]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM notebooks").fetchall()
        return {row["id"]: self._row_to_notebook(row) for row in rows}

    def _all_sources(self) -> dict[str, Source]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM sources").fetchall()
        return {row["id"]: self._row_to_source(row) for row in rows}

    def _all_chunks(self) -> dict[str, SourceChunk]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM source_chunks").fetchall()
        return {row["id"]: self._row_to_chunk(row) for row in rows}

    def _all_guides(self) -> dict[str, SourceGuide]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM source_guides").fetchall()
        return {row["source_id"]: self._row_to_guide(row) for row in rows}

    def _all_solutions(self) -> dict[str, Solution]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM solutions").fetchall()
        return {row["id"]: self._row_to_solution(row) for row in rows}

    def _all_artifacts(self) -> dict[str, Artifact]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM artifacts").fetchall()
        return {row["id"]: self._row_to_artifact(row) for row in rows}

    # ── Phase 2 loaders ───────────────────────────────────────────────────

    def _get_whiteboard_session(self, key: str) -> WhiteboardSession | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM whiteboard_sessions WHERE id=?", (key,)).fetchone()
        return self._row_to_whiteboard_session(row) if row else None

    def _all_whiteboard_sessions(self) -> dict[str, WhiteboardSession]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM whiteboard_sessions").fetchall()
        return {row["id"]: self._row_to_whiteboard_session(row) for row in rows}

    def _get_quiz(self, key: str) -> Quiz | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM quizzes WHERE id=?", (key,)).fetchone()
        return self._row_to_quiz(row) if row else None

    def _all_quizzes(self) -> dict[str, Quiz]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM quizzes").fetchall()
        return {row["id"]: self._row_to_quiz(row) for row in rows}

    def _get_question_paper(self, key: str) -> QuestionPaper | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM question_papers WHERE id=?", (key,)).fetchone()
        return self._row_to_question_paper(row) if row else None

    def _all_question_papers(self) -> dict[str, QuestionPaper]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM question_papers").fetchall()
        return {row["id"]: self._row_to_question_paper(row) for row in rows}

    def _get_attempt(self, key: str) -> Attempt | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM attempts WHERE id=?", (key,)).fetchone()
        return self._row_to_attempt(row) if row else None

    def _all_attempts(self) -> dict[str, Attempt]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM attempts").fetchall()
        return {row["id"]: self._row_to_attempt(row) for row in rows}

    def _get_answer_key(self, key: str) -> AnswerKey | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM answer_keys WHERE id=?", (key,)).fetchone()
        return self._row_to_answer_key(row) if row else None

    def _all_answer_keys(self) -> dict[str, AnswerKey]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM answer_keys").fetchall()
        return {row["id"]: self._row_to_answer_key(row) for row in rows}

    def _get_eval_report(self, key: str) -> EvalReport | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM eval_reports WHERE id=?", (key,)).fetchone()
        return self._row_to_eval_report(row) if row else None

    def _all_eval_reports(self) -> dict[str, EvalReport]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM eval_reports").fetchall()
        return {row["id"]: self._row_to_eval_report(row) for row in rows}

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def make_store_from_env():
    """Select the store implementation from the environment.

    Set STUDYLAB_SQLITE_PATH to use durable SQLite persistence; otherwise the
    in-memory store is used (the default for tests and ephemeral runs).
    """
    from .store import InMemoryStudyLabStore

    path = os.getenv("STUDYLAB_SQLITE_PATH")
    if path:
        return SqliteStudyLabStore(path)
    return InMemoryStudyLabStore()
