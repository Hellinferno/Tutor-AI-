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

The **gateway** exposes the full surface in‑process. `rag` and `solver` expose their slices.

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

## Error format
```json
{ "error": { "code": "not_found" | "bad_request", "message": "…" } }
```
`404` for missing entities (a `KeyError` inside the engine), `400` for bad input
(`ValueError`/`IndexError`).
