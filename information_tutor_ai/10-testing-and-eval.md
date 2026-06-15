# 10 — Testing & Evaluation 🔵

The project's quality gate: what runs, what it proves, and the Phase 1–7 acceptance criteria.

> 🟢 **Plain English:** before code is considered "done," it must pass automatic checks. There are
> two: a **test suite** (does each feature behave correctly?) and an **eval gate** (does the solver
> ever lie about an answer being verified? — that must be zero).

---

## What runs

| Command | What it checks | Current result |
|---|---|---|
| `python -m unittest discover tests` | 190 unit/integration tests | ✅ 190 passed |
| `python packages/eval/run_eval.py` | solver verification gate | ✅ 15 cases, `false_verified_rate=0` |
| `python -m compileall packages services` | every module byte‑compiles (per [Instructions/12](../Instructions/12-testing-strategy.md)) | ✅ clean |
| `cd apps/web && npm run build` | web compiles + type‑checks + prerenders | ✅ green (interactive app) |

CI runs the first two (job `python-test`) and a web manifest check (job `web-static`) on every
push — see [.circleci/config.yml](../.circleci/config.yml).

> 🔒 **Security:** the Phase 4 change set review found **no high/medium‑confidence vulnerabilities**.
> The Phase 6 review surfaced and **fixed** four issues before they shipped: a password‑reset token
> that was returned in the response body (now mock‑gated; production emails it), a malformed bearer
> token that returned 500 instead of 401, an account‑deletion cascade that orphaned
> `answer_keys`/`eval_reports`, and a rate‑limit key that could read a stale user id. Automated
> commit/push security sweeps additionally flagged IDOR + dev‑secret‑fallback risks in the enforced
> auth path, all addressed in Phase 6 (token‑derived identity + per‑user ownership; fail‑fast JWT
> secret).

---

## The test suite (190 tests)

### `tests/test_phase1_core.py` — 12 tests
- **Chunking**: offsets are stable (a chunk's `[start:end]` slice reproduces its text).
- **Grounded ask** uses citations; weak retrieval is **rejected** (`insufficient_source_support`).
- **Hybrid retrieval**: finds exact finance/formula terms; ranks the semantically relevant source
  above a distractor.
- **Qdrant adapter** preserves the hybrid contract metadata.
- **Solver**: symbolic and finance NPV verify; reveal uses the stored solution; cache hit on
  repeat.
- **Artifacts** generate and **mock Notion export** works.
- **OCR** image payload flows into the solver.

### `tests/test_phase1_infra.py` — 12 tests
- **SQLite persistence**: data + cache + revealed step survive a reopen in a new store instance.
- **Sandbox**: code executes and verifies; disallowed imports rejected; dangerous builtins blocked
  by `validate_code`; stdout captured.
- **Prompts**: every registered prompt loads; unknown name raises; placeholders render.
- **Service router**: `Route` matches methods and extracts path params.
- **OCR** solve path.

### `tests/test_phase2_core.py` — 20 tests
- **Teaching**: a session builds a concept progression starting at index 0; next/prev navigate;
  concepts carry explanations, whiteboard elements, and at least one **cited** concept; an empty
  notebook still yields a graceful fallback session.
- **Quizzes**: generates MCQ, true‑false, and short‑answer questions; the default view **hides**
  `correct_answer`; the answer key is fully `verified`; a quiz can be generated **from a topic**
  with no sources.
- **Papers**: generates a sectioned paper with marks + duration; hides answers by default; the
  answer key is `verified`; topic‑only generation works.
- **Eval**: correct answers score full marks; wrong answers score zero; reports include
  `percentage` and a `summary`; paper attempts score too.
- **Edge cases**: quiz/paper generation on an empty notebook (no sources, no topic) raises
  `ValueError`; teaching on an empty notebook does not.

### `tests/test_phase3_core.py` — 20 tests
- **Revision (SM‑2)**: cards generate from notebook concepts; a correct review grows the interval
  and easiness factor; a lapse resets them and re‑queues the card; `due`/`stats` reflect state.
- **Student model**: mastery is computed from eval reports; weak/strong topics split at the
  thresholds; re‑computing replaces (not duplicates) topic rows.
- **Analytics**: per‑attempt trends are returned in order; the user summary aggregates attempts,
  average score, and top weak/strong topics.
- **Voice**: the mock provider round‑trips STT/TTS (`ok`, `text`/`audio_base64`); bad input returns
  `ok: false` with an error.

### `tests/test_phase4_core.py` — 23 tests
- **Connectors**: website/YouTube/audio/Doc/Slides imports become cited, queryable sources; a
  YouTube transcript list is joined; HTML payloads have `<script>`/`<style>` stripped; invalid
  inputs (unsupported type, missing/empty text, missing or non‑absolute url) raise `ValueError`;
  imports are scoped per notebook and meter `source_import` usage.
- **Multi‑agent teaching**: a session builds three cited turns per concept
  (`concept_explainer`/`grounding_verifier`/`practice_coach`); next/prev navigate and set
  `completed`; verifier confidence stays in `[0,1]`.
- **Pricing**: the catalog lists `free/scholar/pro`; a new user defaults to Free; `set_plan`
  changes tier; an unknown tier raises; metering counts usage; quotas report `remaining`/`allowed`
  and block at the limit; Pro is unlimited; the usage summary has one entry per metered action.
- **Persistence**: imports, agent sessions, subscriptions, and usage all survive a SQLite reopen.

### `tests/test_phase5_core.py` — 20 tests
- **Password hashing**: PBKDF2 hashes are salted (two hashes of the same password differ), verify
  correctly, reject wrong passwords, and never contain the plaintext.
- **Auth**: register returns a token and a public user (no hash); login round‑trips and a token
  resolves the user; wrong password, duplicate email, invalid email, and short password are
  rejected; tampered/garbage tokens are rejected; a user survives a SQLite reopen.
- **Authorization**: the owner can access their notebook; a non‑owner raises `PermissionError`.
- **Quota enforcement**: `enforce` blocks once the free quota is spent; Pro is unlimited; the
  `_guard` path returns `402` after the free `source_import` limit when `STUDYLAB_ENFORCE_QUOTAS` is set.
- **Observability**: metrics track asks/solves with correct refusal and verified rates; the snapshot
  has the full shape (incl. solve‑latency percentiles).

### `tests/test_phase6_core.py` — 23 tests
- **Account self‑service**: change password (success / wrong‑current / short‑new rejected); update
  profile; password‑reset flow; a reset token can't be used as a session token; unknown‑email returns
  no token; reset token is **not** returned when auth is enforced.
- **Account deletion**: cascade removes the user's notebooks, sources, subscription, **and** derived
  grading artifacts (`answer_keys`/`eval_reports`) — in both the in‑memory and SQLite stores.
- **Input caps**: over‑cap upload and over‑cap connector import raise; under‑cap passes.
- **Rate limiter**: allows up to the limit then raises; keys are independent; empty spec disables;
  invalid spec raises.
- **JWT‑secret guard**: enforced‑without‑secret raises; enforced‑with‑secret works; dev fallback when
  not enforced; explicit `STUDYLAB_DEV_INSECURE` override.
- **Robustness**: a malformed bearer raises `AuthError` (→ 401), never an uncaught 500.

### `tests/test_phase7_core.py` — 17 tests
- **Sharing**: share/unshare, owner lists shares, "shared with me"; re-sharing the same email
  **updates** the role (no duplicate); unknown email → `KeyError`, bad role → `ValueError`, non-owner
  share/list → `PermissionError`.
- **Authorization**: owner has full access; a `viewer` can read but not edit (raises); an `editor`
  can edit; a non-shared stranger is denied.
- **Roles/admin**: admin is granted via `STUDYLAB_ADMIN_EMAILS`; an admin can `list_users` (no
  hashes); a non-admin cannot.
- **Persistence**: a share and a user's role survive a SQLite reopen; deleting the owner removes the
  shares.

> The gateway HTTP routing for **all Phase 2–7 endpoints** is additionally smoke‑tested end‑to‑end
> against a live `ThreadingHTTPServer`: every route returns 200; with auth enforced, ownership/IDOR
> attempts return 403, missing/malformed tokens 401, over‑quota 402, `/metrics` is gated, **a viewer
> share can read but not upload (403), an editor can, and admin routes reject non-admins (403)**; CORS
> preflight returns 204. The web app passes `tsc --noEmit` + `next build`.

---

## The eval gate

[run_eval.py](../packages/eval/run_eval.py) loads
[benchmarks/phase1_solver.json](../packages/eval/benchmarks/phase1_solver.json) (15 cases across
`symbolic`, `formula`, `code_exec`) and asserts:

1. every `must_verify` case is actually `verified`, **and**
2. no verified answer disagrees with its expected answer → **`false_verified_rate = 0`**.

> The benchmark's expected answers were generated by running each case through the real solver, so
> the gate is meaningful (it would catch any regression that changes a verified answer).

---

## Phase 1 acceptance gate (from the spec)

From [Instructions/10-development-phases.md](../Instructions/10-development-phases.md):

> **Gate:** tests pass, solver eval `false_verified_rate=0`, cited answers include source metadata,
> weak retrieval refuses grounding.

| Gate criterion | Status |
|---|---|
| Tests pass | ✅ 64/64 |
| `false_verified_rate=0` | ✅ |
| Cited answers include source metadata | ✅ (`source_title`, `chunk_index`, offsets, snippet, score) |
| Weak retrieval refuses grounding | ✅ (`insufficient_source_support`) |

➡️ **The Phase 1 gate passes.** Caveat on scope (live Postgres/Qdrant/etc.) in
[11-current-status.md](11-current-status.md).

---

## Phase 2 acceptance gate (from the spec)

From [Instructions/10-development-phases.md](../Instructions/10-development-phases.md), Phase 2 is
*teaching engine with whiteboard, quiz generation, question‑paper generation, verified answer keys,
and auto‑eval/reports.*

| Gate criterion | Status |
|---|---|
| Teaching engine with whiteboard | ✅ (`TeachingEngine`, cited concept progression) |
| Quiz generation (notebook or topic) | ✅ (`QuizEngine`, 3 question types) |
| Question‑paper generation | ✅ (`PaperEngine`, sectioned, marks + duration) |
| Verified answer keys | ✅ (every keyed answer carries `verified` + `verification_method`) |
| Auto‑eval and reports | ✅ (`EvalEngine`: scored attempts → reports) |
| Tests pass | ✅ 20 Phase 2 tests + gateway HTTP smoke test |

➡️ **The Phase 2 gate passes.** As with Phase 1, content is derived deterministically from sources
to keep it offline‑runnable and free of unverified claims.

---

## Phase 3 acceptance gate (from the spec)

From [Instructions/10-development-phases.md](../Instructions/10-development-phases.md), Phase 3 is
*student model, spaced‑repetition schedule, progress analytics, voice I/O, weak‑topic revision cards.*

| Gate criterion | Status |
|---|---|
| Student model | ✅ (`StudentModel`: per‑topic mastery from eval reports) |
| Spaced‑repetition schedule | ✅ (`RepetitionEngine`: SM‑2 cards, due queue, review) |
| Progress analytics | ✅ (`AnalyticsEngine`: trends + user summary) |
| Voice input/output | ✅ (`VoiceProvider`: mock default, Gemini when `GEMINI_API_KEY` set) |
| Weak‑topic revision cards | ✅ (mastery weak topics + card `source=eval_weak_topic`) |
| Tests pass | ✅ 20 Phase 3 tests + gateway HTTP smoke test |

➡️ **The Phase 3 gate passes**, and the web app is wired to all of it (no static mockups). Live
Postgres/Qdrant/Redis and the real voice provider remain env‑gated adapters per
[11-current-status.md](11-current-status.md).

---

## Phase 4 acceptance gate (from the spec)

From [Instructions/10-development-phases.md](../Instructions/10-development-phases.md), Phase 4 is
*multi‑agent teaching, mobile, scaling/pricing/economics, and more source connectors (websites,
YouTube, audio, Google Docs/Slides).*

| Gate criterion | Status |
|---|---|
| More source connectors | ✅ (`SourceConnectorEngine`: website / YouTube / audio / google_doc / google_slides → chunk + guide + cite) |
| Multi‑agent teaching | ✅ (`TeachingEngine.start_multi_agent_session`: explainer / grounding‑verifier / practice‑coach turns per concept) |
| Pricing & economics | ✅ (`PricingEngine`: Free/Scholar/Pro plans, subscriptions, usage metering, quota checks; Stripe seam) |
| Mobile | ◑ Web app is fully **responsive** (phone breakpoints); a **native** app remains later scope per [Instructions/01](../Instructions/01-product-vision.md) |
| Scaling | ◑ The Postgres / Qdrant / Redis **adapter seams** are the scaling path; full horizontal‑scaling infra remains later scope |
| Tests pass | ✅ 23 Phase 4 tests + gateway HTTP smoke test + clean security review |

➡️ **The Phase 4 build deliverables pass.** The two partial items (native mobile, horizontal
scaling) are explicitly *later/out‑of‑scope* in the product vision and engineering‑scope specs, not
Phase‑4 build tasks. Connector fetch‑workers and Stripe billing are env‑gated adapters per
[11-current-status.md](11-current-status.md).

---

## Phase 5 acceptance gate (production readiness)

Phase 5 is not in the original phase list; it was added to deliver the one remaining unbuilt scope
item — **"Full production auth"** from
[Instructions/09-engineering-scope-definition.md](../Instructions/09-engineering-scope-definition.md)
— plus the authorization, quota enforcement, and observability needed for a real launch (the API
contract's `Auth: Bearer JWT`, and the metrics + "private per user" notes in
[Instructions/06](../Instructions/06-api-contracts.md) / [Instructions/11](../Instructions/11-environment-and-devops.md)).

| Gate criterion | Status |
|---|---|
| Authentication (email/password) | ✅ (`AuthEngine`: PBKDF2 hashing, stateless HS256 JWT, register/login) |
| Bearer‑JWT API auth | ✅ (`/v1/auth/*`; gateway enforces when `STUDYLAB_REQUIRE_AUTH=true`) |
| Authorization (private per user) | ✅ (`authorize_notebook` ownership check) |
| Quota enforcement | ✅ (`PricingEngine.enforce` → HTTP 402 when `STUDYLAB_ENFORCE_QUOTAS=true`) |
| Observability metrics | ✅ (`/metrics`: refusal rate, citation coverage, verified rate, cache hit, solve latency) |
| Secrets server‑side only | ✅ (`STUDYLAB_JWT_SECRET` / `STRIPE_API_KEY` read from env; hashes never returned) |
| Tests pass | ✅ 20 Phase 5 tests + gateway HTTP smoke test + clean security review |

➡️ **The Phase 5 gate passes.** Enforcement flags ship **off by default** so the app stays
runnable offline; flipping them on (plus a strong `STUDYLAB_JWT_SECRET`) is the production switch.
OAuth/SSO and a managed metrics backend remain later concerns.

---

## Phase 6 acceptance gate (production hardening + user readiness)

Phase 6 closes the remaining gaps for shipping to real users — the production-hardening concerns in
[Instructions/11-environment-and-devops.md](../Instructions/11-environment-and-devops.md) plus
account self-service — and folds in the fixes from the security reviews.

| Gate criterion | Status |
|---|---|
| Per-user authorization / no IDOR | ✅ (gateway derives identity from the token; ownership enforced on notebooks, sessions, billing, user reads/writes → 403) |
| No forged tokens in prod | ✅ (`make_auth_secret` refuses the dev sentinel when auth is enforced) |
| CORS for the browser app | ✅ (headers on every response + `OPTIONS` 204 preflight; `STUDYLAB_CORS_ORIGINS`) |
| Rate limiting | ✅ (`RateLimiter` → HTTP 429 + `Retry-After` when `STUDYLAB_RATE_LIMIT` set) |
| Input-size caps | ✅ (`STUDYLAB_MAX_SOURCE_CHARS` on upload + connector import → 400) |
| Account self-service | ✅ (change/reset password, edit profile, delete account + full data cascade) |
| Reset-token safety | ✅ (returned only in mock-email mode; never leaked when auth enforced) |
| Readiness probe | ✅ (`/ready`); `/metrics` gated behind auth when enforced |
| Onboarding | ✅ (one-click "Load sample" notebook; account settings UI) |
| Tests pass | ✅ 23 Phase 6 tests + gateway HTTP security smoke test |

➡️ **The Phase 6 gate passes**, and the four review findings (reset-token leak, malformed-token 500,
cascade orphans, stale rate-limit key) plus the automated IDOR/dev-secret sweeps were all fixed and
re-verified. Remaining later work: native mobile, horizontal-scaling infra, OAuth/SSO, and wiring a
reset-email provider — see [11-current-status.md](11-current-status.md).

---

## Phase 7 acceptance gate (collaboration, sharing & roles)

Phase 7 extends the Phase 6 ownership model into multi-user collaboration.

| Gate criterion | Status |
|---|---|
| Notebook sharing | ✅ (`share_notebook`/`unshare_notebook`/`list_shares`; viewer & editor roles) |
| "Shared with me" | ✅ (`list_shared_with_me` → notebooks others shared with the caller) |
| Share-aware authorization | ✅ (`authorize_notebook(require_edit)`: owner or share; viewer = read/ask/generate, editor = +write) |
| Roles | ✅ (`student`/`instructor`/`admin`; admin granted via `STUDYLAB_ADMIN_EMAILS`) |
| Admin-only routes | ✅ (`/v1/admin/users`, `/v1/admin/metrics` → 403 for non-admins) |
| Deletion integrity | ✅ (shares cascade with the notebook and with either party's account) |
| Tests pass | ✅ 17 Phase 7 tests + gateway HTTP collaboration smoke test |

➡️ **The Phase 7 gate passes.** Sharing/admin routes require a logged-in user (bearer token); the
single-user demo experience is unchanged when auth is off. Remaining later work is unchanged: native
mobile, horizontal-scaling infra, OAuth/SSO, and reset-email delivery —
see [11-current-status.md](11-current-status.md).

---

## Phase 8 acceptance gate (classrooms, assignments & class analytics)

Phase 8 turns the dormant `instructor` role from Phase 7 into a real teaching surface: classes,
join codes, assignments, submissions, and per-class analytics.

| Gate criterion | Status |
|---|---|
| Only instructors (or admins) can create classes | ✅ (`create_class` raises `PermissionError` otherwise) |
| Admin can mint instructors | ✅ (`POST /v1/admin/users/{id}/role` → `403` for non‑admins, `400` for bad role) |
| Join codes are unambiguous & unique | ✅ (6‑char alphabet without `O/0/I/1`; retried on collision) |
| Enrollment is idempotent | ✅ (re‑enrolling with the same code returns the existing row) |
| Instructors cannot enroll in their own class | ✅ (`ValueError`) |
| Roster visible only to the class instructor (or admin) | ✅ (student/stranger → `403`) |
| Assignment kind constrained | ✅ (`quiz`/`paper`; the source must live in the instructor's own notebook) |
| Submissions go through the standard eval engine | ✅ (creates an `Attempt`, links via `AssignmentSubmission`) |
| Non‑enrolled cannot submit | ✅ (`PermissionError`) |
| Class analytics reports completion + avg + top weak topics | ✅ (per‑assignment + overall) |
| Persistence | ✅ (classes, enrollments, assignments, submissions survive SQLite reopen) |
| Deletion cascades | ✅ (instructor delete drops classes/assignments/submissions; student delete drops only their enrollment + submissions) |
| Tests pass | ✅ 20 Phase 8 tests covering creation, enrollment, assignments, submissions, analytics, persistence |

➡️ **The Phase 8 gate passes.** Classroom/admin role routes require a logged-in user; the
single-user demo experience (no auth, no classes) is unchanged. Remaining later work is unchanged:
native mobile, horizontal-scaling infra, OAuth/SSO, and reset-email delivery —
see [11-current-status.md](11-current-status.md).

---

## Phase 9 acceptance gate (discussions, instructor feedback & notifications)

Phase 9 makes the Phase 7–8 multi-user product feel connected: comments on shared notebooks,
instructor feedback on submissions, and an inbox of notifications for every multi-user event.

| Gate criterion | Status |
|---|---|
| Notebook comments visible only to access holders | ✅ (`PermissionError` for strangers; viewer share can post + read) |
| Empty/oversized comment bodies rejected | ✅ (`ValueError`) |
| Posting a comment notifies every other access holder | ✅ (`comment_posted`; author is never their own recipient) |
| Submission feedback is instructor‑only | ✅ (student or stranger → `PermissionError`) |
| Override score bounded and used downstream | ✅ (`[0, max_score]`; replaces the auto score in list + analytics) |
| Feedback notifies the student | ✅ (`submission_graded`) |
| Share / enroll / assign / submit emit notifications | ✅ (`notebook_shared`, `class_enrolled`, `assignment_created`, `submission_received`) |
| You can only mark your own notifications read | ✅ (`PermissionError` otherwise) |
| `mark_all_read` zeroes the unread count | ✅ |
| Persistence | ✅ (comments, feedback, notifications survive SQLite reopen) |
| Cascades | ✅ (deleting an owner drops the notebook's comments; deleting a student drops their feedback rows) |
| Tests pass | ✅ 19 Phase 9 tests covering comments, feedback, notifications, and persistence/cascades |

➡️ **The Phase 9 gate passes.** Comments, feedback, and notification routes require a logged-in
user; the single-user demo experience (no auth, no inbox) is unchanged. Remaining later work is
unchanged: native mobile, horizontal-scaling infra, OAuth/SSO, and reset-email delivery — see
[11-current-status.md](11-current-status.md).
