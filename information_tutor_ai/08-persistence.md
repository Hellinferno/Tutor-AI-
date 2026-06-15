# 08 — Persistence (where data lives) 🔵

How Tutor‑AI remembers notebooks, sources, solutions, and artifacts.

> 🟢 **Plain English:** "persistence" just means *saving your data so it's still there after you
> close the app.* Tutor‑AI has three saving options: a quick scratchpad (in‑memory), a real local
> file (SQLite), and a production database (Postgres). They behave the same; you pick one with a
> setting.

---

## Three stores, one interface

All stores expose the **identical method surface**, so the engine never knows or cares which is
active.

| Store | Where data lives | Survives restart? | When to use |
|---|---|:--:|---|
| `InMemoryStudyLabStore` | RAM (Python dicts) | ❌ | Tests, demos, ephemeral runs. **Default.** |
| `SqliteStudyLabStore` | a `.db` file on disk | ✅ | Real local persistence, single‑node deployments. |
| `PostgresStudyLabStore` *(Phase 10)* | a Postgres server (psycopg) | ✅ | Production. Subclasses the SQLite store; SQL is shared and translated via `?` → `%s`. |

Code: [store.py](../packages/studylab_core/studylab_core/store.py),
[store_sqlite.py](../packages/studylab_core/studylab_core/store_sqlite.py),
[store_postgres.py](../packages/studylab_core/studylab_core/store_postgres.py).

---

## How a store is chosen

`make_store_from_env()` reads one environment variable:

```python
# in every service entrypoint
api = StudyLabAPI(make_store_from_env())
```

- `DATABASE_URL` **or** `STUDYLAB_POSTGRES_URL` **set** → `PostgresStudyLabStore()` *(Phase 10)*. If
  the `psycopg` driver isn't installed, the factory **falls through** to SQLite/memory rather
  than refusing to boot — `/v1/admin/storage` confirms what the running process actually picked.
- `STUDYLAB_SQLITE_PATH` **set** → durable `SqliteStudyLabStore(path)`.
- otherwise → `InMemoryStudyLabStore` (default).

```powershell
# durable local run
$env:STUDYLAB_SQLITE_PATH = "data/studylab.db"
python -m services.gateway.app.main
```

> Tests construct `StudyLabAPI()` directly, so they always get a fresh in‑memory store — isolated
> and fast.

---

## The SQLite store in detail

[store_sqlite.py](../packages/studylab_core/studylab_core/store_sqlite.py):

- Creates the tables on first connect — Phase 1 (notebooks, sources, source_chunks, source_guides,
  solutions, artifacts), Phase 2 (whiteboard_sessions, quizzes, question_papers, attempts,
  answer_keys, eval_reports), Phase 3 (revision_cards, sessions, student_profiles,
  topic_masteries), Phase 4 (source_imports, multi_agent_teaching_sessions, subscriptions,
  usage_records), and Phase 5 (users — with `password_hash`) — with the same shape as the Postgres
  migrations.
- Uses **WAL mode** and a re‑entrant lock with `check_same_thread=False` so it's safe under the
  threaded HTTP servers.
- Stores JSON fields (citations, steps, key_concepts) as TEXT; rebuilds dataclasses on read.
- Provides `_TableView` wrappers so attribute access used elsewhere — `store.chunks.values()`,
  `store.guides.get(id)`, `store.artifacts[id]` — works exactly as it did for the in‑memory store.
- Adds `save_solution()` so a **revealed step is written back** and persists across restarts.

### What "durable" buys you (verified by tests)
After writing data and **reopening the same file in a new process**:
- notebooks, sources, chunks, and source guides are still there;
- a grounded `ask` still returns citations;
- a previously solved question returns `from_cache: true`;
- a revealed step is still revealed.

See `tests/test_phase1_infra.py::SqlitePersistenceTests`.

---

## The Postgres target

The migrations define the full production schema (uuid keys, `jsonb`, native enums, indexes):
[001_phase1_foundation.sql](../packages/db/migrations/001_phase1_foundation.sql) (Phase 1 + the
`users`/`sessions`/`revision_cards` stubs), [002_phase2_teaching_quiz.sql](../packages/db/migrations/002_phase2_teaching_quiz.sql)
(teaching, quizzes, papers, eval), and [003_phase3_revision_voice.sql](../packages/db/migrations/003_phase3_revision_voice.sql)
(SM‑2 columns, student_profiles, topic_masteries). The SQLite store mirrors this contract so moving
to Postgres is a store swap, not an engine rewrite.

**Status:** Postgres + Redis are provisioned in `docker-compose.yml`; wiring the app to Postgres
as the live store is an env‑gated next step (see [11-current-status.md](11-current-status.md)).
The Redis cache role is currently served by the store's own solution cache.
