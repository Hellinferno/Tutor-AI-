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

## Error format
```json
{ "error": { "code": "not_found" | "bad_request", "message": "…" } }
```
`404` for missing entities (a `KeyError` inside the engine), `400` for bad input
(`ValueError`/`IndexError`).
