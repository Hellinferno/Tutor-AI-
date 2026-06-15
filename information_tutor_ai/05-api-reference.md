# 05 — API Reference 🔵

Every HTTP endpoint currently implemented. All requests/responses are JSON. The canonical
machine‑readable spec is [docs/openapi.phase1.yml](../docs/openapi.phase1.yml).

> 🟢 **In plain English:** an "endpoint" is a specific web address the app calls to do one thing
> (create a notebook, ask a question, solve a problem). Below, each row is one such action.

---

## Which service serves what

| Capability | Gateway (8000) | RAG service (8001) | Solver service (8002) |
|---|:--:|:--:|:--:|
| Health | ✅ `/health` | ✅ `/health` | ✅ `/health` |
| Create notebook | ✅ | ✅ | — |
| Upload / get source | ✅ | ✅ | — |
| Ask (grounded) | ✅ | ✅ | — |
| Generate artifact | ✅ | ✅ | — |
| Solve / reveal | ✅ | — | ✅ |
| Notion export | ✅ | — | — |
| **Teaching** (start / get / next / prev) | ✅ | ✅ | — |
| **Quizzes** (generate / get / answer‑key / attempt) | ✅ | ✅ | — |
| **Papers** (generate / get / answer‑key / attempt) | ✅ | ✅ | — |
| **Reports** (get / generate) | ✅ | ✅ | — |
| **Revision** (generate-cards / due / stats / review) | ✅ | ✅ | — |
| **Student** (mastery / weak-topics) | ✅ | ✅ | — |
| **Analytics** (trends / summary) | ✅ | ✅ | — |
| **Voice** (stt / tts) | ✅ | ✅ | — |
| **Connectors** (import / list imports) | ✅ | ✅ | — |
| **Multi-agent teaching** (start / get / next / prev) | ✅ | ✅ | — |
| **Billing** (plans / subscription / subscribe / usage) | ✅ | ✅ | — |
| **Auth** (register / login / me) | ✅ | ✅ (register/login) | — |
| **Account** (password change/forgot/reset, profile, delete) | ✅ | — | — |
| **Sharing** (share / unshare / list / shared-with-me) | ✅ | — | — |
| **Admin** (users / metrics — admin role) | ✅ | — | — |
| **Observability** (`/metrics`) | ✅ | ✅ | — |
| **Health/readiness** (`/health`, `/ready`) | ✅ | ✅ (`/health`) | ✅ (`/health`) |

The **gateway** exposes the full surface in‑process. `rag` and `solver` expose their slices.

> ℹ️ Single-resource GET routes are 3 segments after `/v1` (e.g. `/v1/quizzes/{id}`); nested
> reads use path params (e.g. `/v1/student/{user_id}/notebook/{notebook_id}/mastery`). The web
> client ([apps/web/lib/api.ts](../apps/web/lib/api.ts)) and the rag service share these exact shapes.

---

## Endpoints

### `GET /health`
Liveness check. → `{ "status": "ok", "service": "…" }`

### `POST /v1/notebooks`
Create a notebook.
```json
// request
{ "title": "ML Notes", "user_id": "demo-user" }
// response: the created notebook { id, title, user_id, created_at }
```

### `POST /v1/notebooks/{id}/sources/upload`
Add a source; chunks it and generates a source guide.
```json
// request
{ "title": "Gradient Descent", "text": "…", "kind": "notes" }
// response
{ "source": { … }, "source_guide": { summary, key_concepts[], suggested_questions[] } }
```

### `GET /v1/notebooks/{id}/sources/{source_id}`
Fetch a source and its guide.

### `POST /v1/notebooks/{id}/ask`
Grounded question answering.
```json
// request
{ "query": "How does gradient descent update parameters?" }
// response
{
  "answer": "From your sources: 1. … [Gradient Descent, chunk 0]",
  "grounding": "from_sources" | "insufficient_source_support",
  "citations": [ { source_id, source_title, chunk_index, start_char, end_char, snippet, score } ],
  "suggested_followups": [ "…" ]
}
```
If support is weak, `grounding` is `insufficient_source_support` and `citations` is empty — the
**honest refusal**.

### `POST /v1/solve`
Solve and verify a problem (text or OCR).
```json
// request
{ "content": "What is 2 + 2 * 3?", "subject": "analytics", "input_type": "text", "notebook_id": null }
// response
{
  "question_id": "…", "solution_id": "…",
  "answer": "8",
  "steps": [ { idx, text, revealed } ],
  "verified": true,
  "verify_method": "symbolic" | "formula" | "code_exec" | "unverified",
  "from_cache": false,
  "citations": [ … ],
  "latency_ms": 1
}
```
`input_type: "image"` runs the content through the OCR adapter first. Fenced code blocks run in
the sandbox (`verify_method: code_exec`).

### `POST /v1/solve/{solution_id}/reveal`
Reveal one stored step (progressive disclosure).
```json
// request
{ "step_idx": 1 }
// response: the step, now { idx, text, revealed: true }  (persisted)
```

### `POST /v1/notebooks/{id}/artifacts/generate`
Generate a study artifact.
```json
// request
{ "artifact_type": "summary_notes", "title": null }
// response: the artifact { id, artifact_type, title, content_markdown, citations[] }
```

### `POST /v1/notion/export`  *(gateway only)*
Export an artifact to Notion (real API if `NOTION_API_KEY`, else mock when `NOTION_MOCK_EXPORT=true`).
```json
// request
{ "artifact_id": "…", "parent_page_id": null, "data_source_id": null, "mock": true }
// response
{ "connected": true, "message": "…", "page_id": "…", "page_url": "https://notion.local/…" }
```

---

## Phase 2 endpoints — teaching, quizzes, papers, reports

All questions, explanations, and answer keys are derived **deterministically from notebook
sources** (or a supplied `topic`); answer keys carry a `verified` flag and a
`verification_method`.

### `POST /v1/notebooks/{id}/teaching/start`
Start a whiteboard teaching session; returns the concept progression.
```json
// response
{ "id": "session_…", "notebook_id": "…", "current_concept_idx": 0, "completed": false,
  "concepts": [ { "name": "…", "explanation": "From your sources: …",
                  "citations": [ … ], "whiteboard": [ { "type": "math", "katex": "…" } ] } ] }
```

### `GET /v1/teaching/{session_id}`
Fetch a session. `POST /v1/teaching/{session_id}/next` and `…/prev` move the cursor (and set
`completed` at the end). All return the full session object.

### `POST /v1/notebooks/{id}/quizzes/generate`
Generate a quiz from the notebook (or a `topic` when the notebook is empty).
```json
// request
{ "num_questions": 5, "question_types": ["mcq", "true_false", "short_answer"], "topic": null }
// response: { id, notebook_id, title, topic, questions: [ { id, type, question_text,
//             correct_answer, points, difficulty, options?, citations? } ] }
```

### `GET /v1/quizzes/{quiz_id}`  ·  `?include_answers=true`
Fetch a quiz. By default `correct_answer` is blanked (student view); `include_answers=true`
returns the keyed version.

### `POST /v1/quizzes/{quiz_id}/answer-key`
Return the verified answer key: `{ id, source_id, source_type: "quiz", verified, verification_method,
answers: [ { question_id, correct_answer, verified, verification_method, … } ] }`.

### `POST /v1/quizzes/{quiz_id}/attempt`
Submit answers for auto‑grading.
```json
// request
{ "answers": [ { "question_id": "…", "answer": "True" } ] }
// response: an attempt { id, source_id, source_type, total_score, max_score, answers: [ { correct, score, feedback } ] }
```

### `POST /v1/notebooks/{id}/papers/generate`
Generate a sectioned exam paper (defaults to MCQ + true/false + short‑answer sections).
```json
// request
{ "sections": null, "duration_minutes": 60, "topic": null }
// response: { id, title, total_marks, duration_minutes, sections: [ { title, instructions, questions[] } ] }
```

### `GET /v1/papers/{paper_id}` (`?include_answers=true`) · `POST …/answer-key` · `POST …/attempt`
Same shapes as the quiz routes (`source_type: "paper"`). Attempts accept either quiz or paper ids.

### `GET /v1/reports/{attempt_id}`  (also `POST /v1/reports/{attempt_id}/generate`)
Build an evaluation report from a graded attempt.
```json
// response
{ "id": "report_…", "attempt_id": "…", "total_score": 2, "max_score": 2, "percentage": 100.0,
  "per_question": [ … ], "weak_topics": [ … ], "strong_topics": [ … ],
  "summary": "Excellent: 2/2 correct (100.0%). …" }
```

---

## Phase 3 endpoints — revision, student model, analytics, voice

All derived **deterministically** from notebook concepts and the user's own attempt history.

### `POST /v1/notebooks/{id}/revision/generate-cards`
Make spaced‑repetition cards from notebook concepts (or supplied `topics`).
```json
// request:  { "topics": ["gradient descent"] | null, "user_id": "demo-user" }
// response: { "cards": [ { id, topic, due_date, interval_days, state, easiness_factor, correct_streak } ] }
```

### `GET /v1/revision/due?user_id=…`  ·  `GET /v1/revision/stats?user_id=…`
Cards due today → `{ "cards": [ … ] }`. Queue stats → `{ total, due, done, lapsed, avg_easiness }`.

### `POST /v1/revision/{card_id}/review`
Grade a card and reschedule with SM‑2.
```json
// request:  { "card_id": "…", "correct": true }
// response: the updated card (new due_date, interval_days, easiness_factor, streak, state)
```

### `POST /v1/student/{user_id}/mastery`
Recompute a user's topic mastery for a notebook from their eval reports.
```json
// request:  { "notebook_id": "…" }
// response: { user_id, notebook_id, overall_score, masteries: [ { topic, score, attempt_count } ],
//             weak_topics: [ … ], strong_topics: [ … ] }
```

### `GET /v1/student/{user_id}/notebook/{notebook_id}/mastery`  ·  `…/weak-topics`
Read back the stored knowledge state, or just `{ "weak_topics": [ … ] }`.

### `GET /v1/analytics/notebook/{notebook_id}/trends`  ·  `GET /v1/analytics/user/{user_id}/summary`
Per‑attempt score trend → `{ "trends": [ { attempt_id, score, max_score, weak_topics, strong_topics } ] }`.
User summary → `{ total_attempts, avg_score, top_weak_topics, top_strong_topics, total_time_minutes }`.

### `POST /v1/voice/stt`  ·  `POST /v1/voice/tts`
Speech↔text via the env‑gated provider (mock unless `GEMINI_API_KEY` is set).
```json
// stt request: { "audio_base64": "…", "format": "wav" }  → { ok, text, format }
// tts request: { "text": "…", "format": "wav" }           → { ok, audio_base64, format }
```

---

## Phase 4 endpoints — connectors, multi-agent teaching, pricing

New source types, a second teaching mode, and the economics layer. Imported content is chunked,
guided, and cited **identically** to an upload; multi-agent turns are derived deterministically
from the same source guides; plans/quotas/usage are real and tested (only the card charge is gated
behind `STRIPE_API_KEY`).

### `POST /v1/notebooks/{id}/sources/import`
Import a source through a connector. The core does **not** fetch remote content — a connector
worker supplies extracted text / transcript / exported text in `payload`.
```json
// request
{ "connector_type": "website" | "youtube" | "audio" | "google_doc" | "google_slides",
  "title": "GD article",
  "payload": { "url": "https://…", "extracted_text": "…" },   // youtube: transcript[], audio: transcript, docs/slides: exported_text; website also accepts html
  "user_id": "demo-user" }
// response
{ "source": { id, title, kind }, "source_guide": { … },
  "import": { id, connector_type, status, metadata, warnings[] } }
```
Validation errors (unsupported type, missing url, empty text, non‑absolute url) return `400`.

### `GET /v1/notebooks/{id}/imports`
List the connector imports for a notebook → `{ "imports": [ … ], "supported_types": [ … ] }`.

### `POST /v1/notebooks/{id}/agent-teaching/start`
Start a multi‑agent teaching session. Each concept gets three cited turns: an **explainer**, a
**grounding‑verifier** (confidence reflects citation coverage), and a **practice‑coach**.
```json
// response
{ "id": "agent_session_…", "notebook_id": "…", "current_concept_idx": 0, "completed": false,
  "concepts": [ { name, explanation, citations[], whiteboard[] } ],
  "agent_turns": [ { agent_id, role, concept_index, title, content, citations[], confidence } ] }
```

### `GET /v1/agent-teaching/{session_id}`
Fetch a session. `POST /v1/agent-teaching/{session_id}/next` and `…/prev` move the cursor (and set
`completed` at the end). All return the full session object.

### `GET /v1/billing/plans`
List the plan catalog → `{ "plans": [ { tier, name, price_cents, currency, quotas, features[] } ] }`
for `free`, `scholar`, `pro`.

### `GET /v1/billing/subscription/{user_id}`
Return the user's subscription (creates a default Free one on first read) →
`{ id, user_id, tier, status, billing_period, provider, external_id }`.

### `POST /v1/billing/{user_id}/subscribe`
Change plan via the billing provider.
```json
// request:  { "tier": "scholar" }
// response: { "subscription": { … }, "plan": { … },
//             "checkout": { provider, status, checkout_url, external_id, message } }
```
With `STRIPE_API_KEY` set, `checkout_url` is a hosted Checkout Session and the subscription stays
`past_due` until a webhook confirms; in mock mode it activates immediately.

### `POST /v1/billing/{user_id}/usage`  ·  `GET /v1/billing/usage/{user_id}`
Record a metered action → the usage record; or read the period summary →
`{ user_id, tier, status, billing_period, provider, price_cents, currency,
   actions: [ { action, used, limit, remaining, allowed } ] }`.
Metered actions: `ask`, `solve`, `quiz`, `paper`, `artifact`, `source_import`, `teaching`.

---

## Phase 5 endpoints — auth & observability

First‑party email/password auth issues a stateless **HS256 JWT** (signed with `STUDYLAB_JWT_SECRET`;
passwords stored with PBKDF2‑HMAC‑SHA256). Auth endpoints always work; the gateway only *requires* a
token when `STUDYLAB_REQUIRE_AUTH=true` (everything except `/health`, `/metrics`, `/v1/auth/register`,
`/v1/auth/login` then needs `Authorization: Bearer <token>`).

### `POST /v1/auth/register`
Create an account and return a token.
```json
// request:  { "email": "dia@example.com", "password": "min-8-chars", "subject_domain": "ai_ds" }
// response: { "user": { id, email, subject_domain, prefs, created_at }, "token": "…", "token_type": "Bearer" }
```
The returned `user` never includes the password hash. Duplicate email, invalid email, or a
password under 8 characters return `401`.

### `POST /v1/auth/login`
Authenticate and return a token.
```json
// request:  { "email": "dia@example.com", "password": "…" }
// response: { "user": { … }, "token": "…", "token_type": "Bearer" }
```
Invalid credentials return `401`.

### `GET /v1/auth/me`
Return the user for the supplied `Authorization: Bearer <token>` (a malformed/expired/tampered token
returns `401`).

### `GET /metrics`  (also `GET /v1/admin/metrics`)
Observability snapshot — the production signals from
[Instructions/11](../Instructions/11-environment-and-devops.md):
```json
{
  "asks": 12, "weak_retrieval_refusal_rate": 0.17, "citation_coverage_rate": 0.83,
  "solves": 9, "verified_rate": 1.0, "false_verified_rate": 0.0, "cache_hit_rate": 0.22,
  "solve_latency_ms": { "p50": 1, "p90": 3, "p99": 8 },
  "notion_export_success_rate": 1.0
}
```

> **Quota enforcement:** when `STUDYLAB_ENFORCE_QUOTAS=true`, a metered action that exceeds the plan
> quota returns **`402` `quota_exceeded`** with a `quota` object (`action`, `used`, `limit`,
> `remaining`). With the flag off (default) usage is metered but never blocked.

---

## Phase 6 endpoints — account self-service & hardening

Account routes require a valid `Authorization: Bearer <token>` (they act on *the token's* user —
never a path/payload user id). The forgot/reset routes are public (token-based).

### `POST /v1/auth/password/change`
Change the authenticated user's password.
```json
// request:  { "current_password": "…", "new_password": "min-8-chars" }   // response: public user
```
Wrong current password or a too-short new password returns `401`.

### `POST /v1/auth/password/forgot`  ·  `POST /v1/auth/password/reset`
Request a reset, then set a new password with the purpose-scoped reset token.
```json
// forgot request: { "email": "dia@example.com" }  → { "ok": true, "reset_token": "…"|null }
// reset  request: { "token": "…", "password": "min-8-chars" }  → public user
```
The `reset_token` is returned in the body **only in mock-email mode** (auth not enforced, or
`STUDYLAB_AUTH_MOCK_EMAIL` set); in production it is delivered out-of-band and the response only
confirms receipt. A reset token cannot be used as a session token (purpose-scoped).

### `POST /v1/auth/profile`
Update the authenticated user's `subject_domain` and/or `prefs` → public user.

### `POST /v1/auth/delete`
Delete the authenticated user's account and **cascade** all their data (notebooks, sources, chunks,
guides, artifacts, sessions, quizzes/papers, imports, attempts, answer keys, eval reports, revision
cards, mastery, subscription, usage) → `{ "ok": true, "deleted": "<user_id>" }`.

### `GET /ready`
Readiness probe (no auth) → `{ "status": "ready", "version": "0.6.0", "store": "SqliteStudyLabStore" }`.
`GET /health` returns `{ "status": "ok", "version": "0.6.0" }`.

### Hardening behaviour (all routes)
- **CORS:** every response carries `Access-Control-Allow-*`; `OPTIONS` preflight returns `204`.
  Allowed origin is `STUDYLAB_CORS_ORIGINS` (default `*`).
- **Rate limiting:** when `STUDYLAB_RATE_LIMIT="requests/seconds"` is set, exceeding it returns
  **`429` `rate_limited`** with a `Retry-After` header (keyed by user when authenticated, else IP).
- **Input caps:** source upload/import over `STUDYLAB_MAX_SOURCE_CHARS` (default 1,000,000) returns `400`.
- **Auth gate:** with `STUDYLAB_REQUIRE_AUTH=true`, every non-public route needs a bearer token
  (else `401`); accessing another user's notebook/resource returns **`403` `forbidden`**.

---

## Phase 7 endpoints — collaboration, sharing & roles

Sharing and admin routes always act as **the logged-in user** (bearer token required, else `401`).
A `viewer` share grants read / ask / generate; an `editor` share also grants source writes
(upload/import). `authorize_notebook` now allows the owner **or** a shared user; cross-access is `403`.

### `POST /v1/notebooks/{id}/shares`
Share a notebook (owner only) with another user by email.
```json
// request:  { "email": "classmate@example.com", "role": "viewer" }   // or "editor"
// response: the share { id, notebook_id, owner_id, shared_with_id, shared_with_email, role, created_at }
```
Re-sharing the same email updates the role (no duplicate). Unknown email → `404`; bad role → `400`;
non-owner → `403`.

### `GET /v1/notebooks/{id}/shares`  ·  `POST /v1/notebooks/{id}/shares/remove`
List a notebook's shares (owner only) → `{ "shares": [ … ] }`; revoke one →
`{ "ok": true, "removed": "<share_id>" }` (request `{ "share_id": "…" }`).

### `GET /v1/notebooks/shared-with-me`
Notebooks shared with the caller → `{ "shared_with_me": [ { share_id, notebook_id, title, role, owner_id } ] }`.

### `GET /v1/admin/users`  ·  `GET /v1/admin/metrics`  *(admin role required → else `403`)*
List users (public shape, no hashes) and the metrics snapshot. Admin is granted at registration to
emails in `STUDYLAB_ADMIN_EMAILS`.

> Write-vs-view: source **upload** and connector **import** require an `editor` share (or ownership);
> reads, ask, and material generation (quizzes/papers/teaching/artifacts) are allowed for `viewer`.

---

## Error format
```json
{ "error": { "code": "not_found" | "bad_request", "message": "…" } }
```
`404` for missing entities (a `KeyError` inside the engine), `400` for bad input
(`ValueError`/`IndexError`).
