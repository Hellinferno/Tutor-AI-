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
         ├─< sessions                                  (Phase 3)
         ├─< revision_cards                            (Phase 3)
         ├─< whiteboard_sessions                       (Phase 2)
         ├─< multi_agent_teaching_sessions             (Phase 4)
         ├─< source_imports >── sources                (Phase 4)
         ├─< quizzes ──< quiz_questions                (Phase 2)
         └─< question_papers ──< paper_sections        (Phase 2)

attempts >── quiz | paper      (source_id + source_type)   (Phase 2)
  └─1 eval_reports                                          (Phase 2)
answer_keys >── quiz | paper   (source_id + source_type)    (Phase 2)

(user_id, notebook_id) ─1 student_profiles ──< topic_masteries   (Phase 3)

users ──< subscriptions        (latest row = current plan)   (Phase 4)
users ──< usage_records        (one per metered action)       (Phase 4)
users.role (student|instructor|admin)                         (Phase 7)
notebooks ──< notebook_shares >── users (shared_with)          (Phase 7)

users (instructor) ──< classes                                 (Phase 8)
classes ──< class_enrollments >── users (student)              (Phase 8)
classes ──< assignments → quiz | paper (source_id + kind)      (Phase 8)
assignments ──< assignment_submissions ─1 attempts             (Phase 8)
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
Now **active in Phase 3** (see the Phase 3 tables below). `sessions` logs study/quiz/paper/revision
interactions (with a `kind`); `revision_cards` drives spaced repetition.

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

## Phase 3 tables (memory, mastery, sessions)

Added in [003_phase3_revision_voice.sql](../packages/db/migrations/003_phase3_revision_voice.sql)
(Postgres) and mirrored in the SQLite store. *(Voice is stateless — `VoiceResult` is returned, not
stored.)*

### `revision_cards`
A spaced‑repetition flashcard: `id`, `user_id`, `notebook_id`, `topic`, `due_date`,
`interval_days`, `state` (`queued|done|lapsed`), `easiness_factor`, `correct_streak`, `source`
(`manual|eval_weak_topic`). Reviews apply an SM‑2 update.

### `sessions`
A study session log: `id`, `user_id`, `notebook_id`, `kind` (`study|quiz|paper|revision`),
`started_at`, `ended_at`, `interactions` (JSON). Used by analytics for study time.

### `student_profiles` & `topic_masteries`
- `student_profiles`: one per `(user_id, notebook_id)`, with `updated_at`.
- `topic_masteries`: `student_profile_id`, `topic`, `score` (0–1), `attempt_count`,
  `last_attempt_date`. Unique on `(student_profile_id, topic)`; recomputed from eval reports.

---

## Phase 4 tables (connectors, multi-agent teaching, pricing)

Added in
[004_phase4_connectors_agents_billing.sql](../packages/db/migrations/004_phase4_connectors_agents_billing.sql)
(Postgres) and mirrored in the SQLite store.

### `source_imports`
Connector provenance for an imported source: `id`, `notebook_id`, `source_id` (the real row in
`sources`), `connector_type` (`website|youtube|audio|google_doc|google_slides`), `title`, `status`,
`metadata` (JSON — url/video_id/document_id/language/etc.), `warnings` (JSON), `created_at`. The
imported text itself lives in `sources`/`source_chunks` exactly like an upload, so retrieval and
citations are identical.

### `multi_agent_teaching_sessions`
A multi‑agent walk‑through: `id`, `notebook_id`, `current_concept_idx`, `concepts` (JSON, same shape
as a whiteboard session), `agent_turns` (JSON — each turn has `agent_id`, `role`, `concept_index`,
`title`, `content`, `citations`, `confidence`), `completed`. Three turns per concept
(`concept_explainer`, `grounding_verifier`, `practice_coach`).

### `subscriptions`
One current plan per user (latest row wins): `id`, `user_id`, `tier` (`free|scholar|pro`), `status`
(`active|past_due|canceled`), `billing_period` (`YYYY-MM`), `provider` (`mock|stripe`),
`external_id` (provider id), `created_at`, `updated_at`.

### `usage_records`
One row per metered action: `id`, `user_id`, `action`
(`ask|solve|quiz|paper|artifact|source_import|teaching`), `billing_period` (`YYYY-MM`), `quantity`,
`created_at`. Quota checks sum these against the plan's quota for the period. *(Plans/quotas live in
the `PLAN_CATALOG` in [pricing.py](../packages/studylab_core/studylab_core/pricing.py), not a table.)*

---

## Phase 5 tables (authentication)

Added in [005_phase5_auth_observability.sql](../packages/db/migrations/005_phase5_auth_observability.sql)
(Postgres) and mirrored in the SQLite store. The `users` table now carries credentials so the local
store backs first‑party auth (it previously existed only as the spec's Postgres target).

### `users`
`id`, `email` (unique), `password_hash` (PBKDF2‑HMAC‑SHA256, stored as
`pbkdf2_sha256$iterations$salt$hash` — never the plaintext), `subject_domain` (`ai_ds|analytics|finance`),
`prefs` (JSON), `created_at`. JWTs are **stateless** (HS256, signed with `STUDYLAB_JWT_SECRET`), so
there is no sessions/tokens table; observability metrics are in‑process counters, not persisted.

> **Phase 6 — account deletion:** `delete_user` cascades a user's owned data across every table —
> their notebooks and notebook‑scoped rows (sources, chunks, guides, artifacts, whiteboard/agent
> sessions, quizzes, papers, source imports), the derived grading rows (answer keys, eval reports),
> and their user‑scoped rows (attempts, revision cards, sessions, student profiles + topic masteries,
> subscriptions, usage records) — before removing the `users` row. No schema change (migration 006 is
> indexes only); the cascade is enforced in both the in‑memory and SQLite stores.

---

## Phase 7 tables (collaboration & roles)

Added in [007_phase7_sharing_roles.sql](../packages/db/migrations/007_phase7_sharing_roles.sql)
(Postgres) and mirrored in the SQLite store.

### `users.role`
A `role` column on `users` (`student` | `instructor` | `admin`, default `student`). Admin is granted
at registration to emails in `STUDYLAB_ADMIN_EMAILS`; admin-only routes (`/v1/admin/*`) check it.

### `notebook_shares`
One row per (notebook, recipient): `id`, `notebook_id`, `owner_id`, `shared_with_id`,
`shared_with_email`, `role` (`viewer` | `editor`), `created_at`; unique on
`(notebook_id, shared_with_id)`. A `viewer` share grants read / ask / generate; an `editor` share
also grants source writes. `authorize_notebook(require_edit=…)` allows the owner **or** a share of
sufficient role. Shares cascade-delete with the notebook and with either party's account deletion.

---

## Phase 8 tables (classrooms, assignments & analytics)

Added in [008_phase8_classrooms.sql](../packages/db/migrations/008_phase8_classrooms.sql) (Postgres)
and mirrored in the SQLite store.

### `classes`
`id`, `instructor_id` → `users(id)`, `name`, `code` (unique 6‑char join code, unambiguous alphabet),
`created_at`. Only users with role `instructor` or `admin` can create one. The code is the
instructor's secret: it's returned to the instructor (and to admins) but never to enrolled students.

### `class_enrollments`
One row per (class, student): `id`, `class_id`, `student_id`, `joined_at`; unique on
`(class_id, student_id)` so re-enrolling is a no-op. Students enroll via `POST /v1/classes/enroll`
with the class's `code`. Instructors cannot enroll in their own class.

### `assignments`
A class-scoped pointer at an existing quiz/paper: `id`, `class_id`, `kind` (`quiz` | `paper`),
`source_id` (quiz_id / paper_id), `title`, `due_at` (nullable), `created_at`. The instructor must
own the notebook the source belongs to (otherwise `403`).

### `assignment_submissions`
Links a student's `Attempt` back to the assignment so the instructor can see class-wide submissions:
`id`, `assignment_id`, `student_id`, `attempt_id` → `attempts(id)`, `submitted_at`. Created by
`POST /v1/assignments/{id}/submit`, which runs the standard eval engine and writes both the
attempt and the submission row.

> **Cascades.** Deleting an instructor's account drops their classes, all of those classes' assignments
> and submissions, and their enrollment rows. Deleting a student drops only their enrollment and
> submission rows (the class survives for the instructor).

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
| `revision_card.state` (Phase 3) | `queued`, `done`, `lapsed` |
| `session.kind` (Phase 3) | `study`, `quiz`, `paper`, `revision` |
| `connector_type` (Phase 4) | `website`, `youtube`, `audio`, `google_doc`, `google_slides` |
| `plan_tier` (Phase 4) | `free`, `scholar`, `pro` |
| `metered_action` (Phase 4) | `ask`, `solve`, `quiz`, `paper`, `artifact`, `source_import`, `teaching` |
| `subscription.status` (Phase 4) | `active`, `past_due`, `canceled` |
| `subject_domain` (Phase 5, user) | `ai_ds`, `analytics`, `finance` |
| `role` (Phase 7, user) | `student`, `instructor`, `admin` |
| `share.role` (Phase 7) | `viewer`, `editor` |
| `assignment.kind` (Phase 8) | `quiz`, `paper` |

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
