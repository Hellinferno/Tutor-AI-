# 04 — Data Model 🔵

What the system stores. There are two representations that stay in sync:

- **Python dataclasses** in [models.py](../packages/studylab_core/studylab_core/models.py) — what
  the engine works with at runtime.
- **SQL tables** — the Postgres schema in
  [001_phase1_foundation.sql](../packages/db/migrations/001_phase1_foundation.sql) +
  [002_phase2_teaching_quiz.sql](../packages/db/migrations/002_phase2_teaching_quiz.sql) (production
  target) and the matching SQLite tables created by
  [store_sqlite.py](../packages/studylab_core/studylab_core/store_sqlite.py) (durable local).

> 🟢 **In plain English:** this is the app's memory. Each "table" is like a spreadsheet: one row
> per thing (a notebook, a source, an answer), with named columns. The diagram shows how they
> link — e.g. a *source* belongs to a *notebook*, and a *chunk* belongs to a *source*.

---

## Entity relationships

```
users
  └─< notebooks
         ├─< sources ──< source_chunks
         │        └─1 source_guides
         ├─< artifacts
         ├─< questions ──< solutions
         ├─< sessions
         ├─< revision_cards
         ├─< whiteboard_sessions                       (Phase 2)
         ├─< quizzes ──< quiz_questions                (Phase 2)
         └─< question_papers ──< paper_sections        (Phase 2)

attempts >── quiz | paper      (source_id + source_type)   (Phase 2)
  └─1 eval_reports                                          (Phase 2)
answer_keys >── quiz | paper   (source_id + source_type)    (Phase 2)
```
`└─<` = one‑to‑many, `└─1` = one‑to‑one. (`users` and `notebooks` may be null on some rows in the
current local flow, which defaults the owner to `demo-user`.)

---

## Tables (current schema)

### `notebooks`
A study container. `id`, `user_id`, `title`, `created_at`.

### `sources`
An uploaded piece of material in a notebook. `id`, `notebook_id`, `title`, `kind`
(`pdf|notes|slides|text|other`), `status`, `text_sha256`, `created_at`. *(The local store also
keeps the raw `text`.)*

### `source_chunks`
A source split into retrievable pieces with **exact character offsets** so citations can point to
a precise span. `id`, `source_id`, `notebook_id`, `chunk_index`, `text`, `start_char`,
`end_char`, `vector_id`. Unique on `(source_id, chunk_index)`.

### `source_guides`
One per source: `summary`, `key_concepts` (JSON), `suggested_questions` (JSON).

### `questions` & `solutions`
- `questions`: canonical text + a `hash` for de‑duplication/caching, `subject`, optional
  `notebook_id`.
- `solutions`: `steps` (JSON), `answer`, `verify_method`
  (`code_exec|symbolic|formula|self_consistency|cross_model|unverified`), `verified` (bool),
  `citations` (JSON). This is what powers caching and step‑reveal.

### `artifacts`
A generated study document: `artifact_type`
(`summary_notes|study_guide|planner|timetable|revision_cards`), `title`, `content_markdown`,
`citations` (JSON), optional `notion_page_url`.

### `sessions` & `revision_cards`
Schema exists for upcoming phases: `sessions` (interaction logs) and `revision_cards` (spaced
repetition with `due_date`, `interval_days`, `state`). *Defined now, exercised in Phase 3.*

---

## Phase 2 tables (teaching, quizzes, papers, eval)

Added in [002_phase2_teaching_quiz.sql](../packages/db/migrations/002_phase2_teaching_quiz.sql)
(Postgres) and mirrored in the SQLite store.

### `whiteboard_sessions`
A teaching walk‑through: `id`, `notebook_id`, `current_concept_idx`, the `concepts` progression
(JSON — each concept has `name`, `explanation`, `citations`, `whiteboard` elements), `completed`.

### `quizzes` & `quiz_questions`
- `quizzes`: `id`, `notebook_id`, `title`, optional `topic`, `num_questions`.
- `quiz_questions`: `type` (`mcq|true_false|short_answer`), `question_text`, `options` (JSON),
  `correct_answer`, `points`, `difficulty`, `citations` (JSON), `idx`. *(The SQLite store nests
  questions as JSON inside the quiz row.)*

### `question_papers` & `paper_sections`
- `question_papers`: `id`, `notebook_id`, `title`, `total_marks`, `duration_minutes`.
- `paper_sections`: `title`, `instructions`, `idx`, with the same question shape as quizzes.

### `attempts`
A graded submission: `source_id` + `source_type` (`quiz|paper`), `user_id`, `answers` (JSON, per
question: `given_answer`, `correct`, `score`, `feedback`), `total_score`, `max_score`.

### `answer_keys`
The verified key for a quiz or paper: `source_id` + `source_type`, `answers` (JSON), `verified`
(bool), `verification_method` (e.g. `mcq_option_check`, `boolean_key_check`,
`source_citation_check`).

### `eval_reports`
A report built from an attempt: `attempt_id`, `total_score`, `max_score`, `percentage`,
`per_question` (JSON), `weak_topics` (JSON), `strong_topics` (JSON), `summary`.

---

## Enumerated types

| Type | Values |
|---|---|
| `source_kind` | `pdf`, `notes`, `slides`, `text`, `other` |
| `artifact_type` | `summary_notes`, `study_guide`, `planner`, `timetable`, `revision_cards` |
| `verify_method` | `code_exec`, `symbolic`, `formula`, `self_consistency`, `cross_model`, `unverified` |
| `grounding` (response field) | `from_sources`, `general_knowledge`, `insufficient_source_support` |
| `question_type` (Phase 2) | `mcq`, `true_false`, `short_answer` |
| `attempt_source_type` (Phase 2) | `quiz`, `paper` |
| `difficulty` (Phase 2) | `easy`, `medium`, `hard` |

---

## How the two stores represent it

| Concern | Postgres (target) | SQLite (durable local) |
|---|---|---|
| IDs | `uuid` | `prefix_hex` text ids (e.g. `notebook_ab12…`) |
| JSON columns | `jsonb` | `TEXT` holding JSON |
| Enums | native `ENUM` types | plain `TEXT` (values enforced in code) |
| Timestamps | `timestamptz` | ISO‑8601 `TEXT` |

The **in‑memory** store keeps the same dataclasses in Python dictionaries. All three present the
identical method surface, so the engine code is unaware of which one is active. See
[08-persistence.md](08-persistence.md).
