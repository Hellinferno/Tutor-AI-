from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import asdict, is_dataclass
from typing import Any, Callable
from uuid import uuid4

from .models import Artifact, Citation, Notebook, Solution, Source, SourceChunk, SourceGuide


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
            self._conn.commit()

        self.notebooks = _TableView(self._all_notebooks, self._get_notebook)
        self.sources = _TableView(self._all_sources, self._get_source)
        self.chunks = _TableView(self._all_chunks, self._get_chunk)
        self.guides = _TableView(self._all_guides, self.get_guide)
        self.solutions = _TableView(self._all_solutions, self._get_solution)
        self.artifacts = _TableView(self._all_artifacts, self._get_artifact)

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
