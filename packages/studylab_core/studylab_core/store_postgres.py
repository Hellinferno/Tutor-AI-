"""Phase 10: durable Postgres-backed store.

Mirrors :class:`SqliteStudyLabStore` so every engine that already runs against the
in-memory + SQLite stores keeps working — including auth, sharing, classrooms,
discussions, feedback, and notifications. The only structural difference is the
connection layer:

* psycopg (psycopg3) is the production driver; it's imported **lazily** so the
  module still loads in environments without it (CI, the default offline run).
* SQL is translated from the SQLite store's ``?`` placeholders to psycopg's
  ``%s`` at the point of execution by ``_PgConnAdapter``.
* SQLite PRAGMAs and the SQLite-specific ``_ensure_compat_columns`` shim are
  no-ops on Postgres: a fresh schema already has every column.

Activate it by setting ``DATABASE_URL`` (or the explicit ``STUDYLAB_POSTGRES_URL``);
see :func:`make_store_from_env` in ``store_sqlite``.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from .store_sqlite import SCHEMA, SqliteStudyLabStore


def _load_psycopg():
    """Lazy import so this module is importable without psycopg installed."""

    try:
        import psycopg  # type: ignore  # psycopg3
        from psycopg.rows import dict_row  # type: ignore

        return psycopg, dict_row
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "PostgresStudyLabStore requires the `psycopg` (psycopg3) package. "
            "Install with `pip install \"psycopg[binary]\"`."
        ) from exc


class _PgCursor:
    """Wraps a psycopg cursor so callers can chain ``.fetchone()``/``.fetchall()``.

    SQLite's ``conn.execute(sql, params)`` returns a Cursor directly; psycopg's
    cursor must be obtained from the connection first. This shim keeps the
    SQLite-store call sites unchanged.
    """

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)


class _PgConnAdapter:
    """Mirrors the slice of sqlite3.Connection that SqliteStudyLabStore uses.

    Translates ``?`` -> ``%s`` for psycopg and yields dict-keyed rows so the SQLite
    store's ``row["col"]`` accesses work unchanged.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, params: tuple | list = ()) -> _PgCursor:
        translated = sql.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(translated, params)
        return _PgCursor(cur)

    def executescript(self, script: str) -> None:
        # psycopg accepts multi-statement scripts via a single execute call.
        cur = self._conn.cursor()
        cur.execute(script)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class PostgresStudyLabStore(SqliteStudyLabStore):
    """Durable Postgres-backed store. Same surface as :class:`SqliteStudyLabStore`."""

    def __init__(self, dsn: str | None = None) -> None:
        psycopg, dict_row = _load_psycopg()
        self.dsn = dsn or os.getenv("STUDYLAB_POSTGRES_URL") or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL not set")
        # autocommit=False so the SQLite store's explicit commits still control the txn.
        raw = psycopg.connect(self.dsn, autocommit=False, row_factory=dict_row)
        self._lock = threading.RLock()
        self._conn = _PgConnAdapter(raw)
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._ensure_compat_columns()
            self._conn.commit()
        self._init_views()

    def _init_views(self) -> None:
        """Set up the in-memory dict-like table views the SQLite store exposes."""

        # Re-run only the table-view wiring half of SqliteStudyLabStore.__init__.
        # This is the chunk that follows ``executescript(SCHEMA)`` there — every
        # engine reads through ``self.<table>`` so the views must exist.
        from .store_sqlite import _TableView

        self.users = _TableView(self._all_users, self._get_user)
        self.notebooks = _TableView(self._all_notebooks, self._get_notebook)
        self.sources = _TableView(self._all_sources, self._get_source)
        self.chunks = _TableView(self._all_chunks, self._get_chunk)
        self.guides = _TableView(self._all_guides, self.get_guide)
        self.source_imports = _TableView(self._all_source_imports, self._get_source_import)
        self.solutions = _TableView(self._all_solutions, self._get_solution)
        self.artifacts = _TableView(self._all_artifacts, self._get_artifact)
        self.whiteboard_sessions = _TableView(self._all_whiteboard_sessions, self._get_whiteboard_session)
        self.multi_agent_teaching_sessions = _TableView(
            self._all_multi_agent_teaching_sessions, self._get_multi_agent_teaching_session
        )
        self.quizzes = _TableView(self._all_quizzes, self._get_quiz)
        self.question_papers = _TableView(self._all_question_papers, self._get_question_paper)
        self.attempts = _TableView(self._all_attempts, self._get_attempt)
        self.answer_keys = _TableView(self._all_answer_keys, self._get_answer_key)
        self.eval_reports = _TableView(self._all_eval_reports, self._get_eval_report)
        self.revision_cards = _TableView(self._all_revision_cards, self._get_revision_card)
        self.sessions = _TableView(self._all_sessions, self._get_session)
        self.student_profiles = _TableView(self._all_student_profiles, self._get_student_profile)
        self.topic_masteries = _TableView(self._all_topic_masteries, self._get_topic_mastery)
        self.subscriptions = _TableView(self._all_subscriptions, self._get_subscription)
        self.usage_records = _TableView(self._all_usage_records, self._get_usage_record)
        self.classes = _TableView(self._all_classes_map, self._get_class)
        self.enrollments = _TableView(self._all_enrollments_map, self._get_enrollment)
        self.assignments = _TableView(self._all_assignments_map, self._get_assignment)
        self.submissions = _TableView(self._all_submissions_map, self._get_submission)
        self.comments = _TableView(self._all_comments_map, self._get_comment)
        self.submission_feedback = _TableView(self._all_feedback_map, self._get_feedback)
        self.notifications = _TableView(self._all_notifications_map, self._get_notification)

    def _ensure_compat_columns(self) -> None:
        # SQLite shim uses PRAGMA table_info / ALTER TABLE ADD COLUMN; Postgres
        # supports ``ADD COLUMN IF NOT EXISTS`` natively so we just apply the
        # same backfills idempotently. Schema additions Phase 5+ already covered
        # in SCHEMA via ``CREATE TABLE IF NOT EXISTS``; the role/kind columns get
        # explicit ``IF NOT EXISTS`` here because the same table can pre-exist
        # in a stage Postgres from earlier phases.
        for sql in (
            "ALTER TABLE answer_keys ADD COLUMN IF NOT EXISTS verified INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE answer_keys ADD COLUMN IF NOT EXISTS verification_method TEXT NOT NULL DEFAULT 'deterministic_source_check'",
            "ALTER TABLE revision_cards ADD COLUMN IF NOT EXISTS easiness_factor REAL NOT NULL DEFAULT 2.5",
            "ALTER TABLE revision_cards ADD COLUMN IF NOT EXISTS correct_streak INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE revision_cards ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual'",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'study'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'student'",
        ):
            try:
                self._conn.execute(sql)
            except Exception:
                # Already applied or table doesn't exist in this fresh-schema run.
                pass
