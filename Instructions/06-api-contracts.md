# 06 - API Contracts

Base: `/v1`. Auth: Bearer JWT. JSON errors: `{ "error": { "code": "...", "message": "..." } }`.

## Notebooks

### POST /v1/notebooks
Req:
```json
{ "title": "Corporate Finance Week 3", "user_id": "demo-user" }
```
Resp:
```json
{ "id": "notebook_123", "title": "Corporate Finance Week 3", "user_id": "demo-user", "created_at": "..." }
```

## Sources

### POST /v1/notebooks/{notebook_id}/sources/upload
Req:
```json
{ "title": "NPV Notes", "kind": "notes", "text": "Net present value discounts..." }
```
Resp:
```json
{
  "source": { "id": "source_123", "notebook_id": "notebook_123", "title": "NPV Notes", "status": "ready" },
  "source_guide": {
    "source_id": "source_123",
    "summary": "...",
    "key_concepts": ["npv", "cash", "flow"],
    "suggested_questions": ["What are the main ideas about npv?"]
  }
}
```

### GET /v1/notebooks/{notebook_id}/sources/{source_id}
Resp: source metadata plus source guide.

## Notebook ask

### POST /v1/notebooks/{notebook_id}/ask
Req:
```json
{ "query": "What is the NPV formula?" }
```
Resp:
```json
{
  "answer": "From your sources: ...",
  "grounding": "from_sources",
  "citations": [
    {
      "source_id": "source_123",
      "source_title": "NPV Notes",
      "chunk_index": 0,
      "start_char": 0,
      "end_char": 420,
      "snippet": "Net present value discounts...",
      "score": 0.82
    }
  ],
  "suggested_followups": ["Explain npv using this source."]
}
```

If evidence is weak:
```json
{
  "answer": "I do not have enough support in your uploaded sources...",
  "grounding": "insufficient_source_support",
  "citations": []
}
```

## Solve

### POST /v1/solve
Req:
```json
{
  "input_type": "text",
  "content": "Calculate NPV at 10% for cash flows -100, 60, 60.",
  "subject": "finance",
  "notebook_id": "notebook_123"
}
```
Resp:
```json
{
  "question_id": "question_123",
  "solution_id": "solution_123",
  "answer": "4.13",
  "steps": [{"idx": 0, "text": "...", "revealed": true}],
  "verified": true,
  "verify_method": "formula",
  "from_cache": false,
  "citations": [],
  "latency_ms": 12
}
```

### POST /v1/solve/{solution_id}/reveal
Req:
```json
{ "step_idx": 2 }
```
Resp: stored solution step. This must not trigger a new solve.

## Artifacts

### POST /v1/notebooks/{notebook_id}/artifacts/generate
Req:
```json
{ "artifact_type": "summary_notes", "title": "Week 3 Summary" }
```
Allowed types: `summary_notes`, `study_guide`, `planner`, `timetable`, `revision_cards`.

## Notion export

### POST /v1/notion/export
Req:
```json
{
  "artifact_id": "artifact_123",
  "parent_page_id": null,
  "data_source_id": null,
  "mock": false
}
```
Resp:
```json
{ "connected": true, "message": "Created Notion page.", "page_url": "https://notion.so/..." }
```

If Notion is not connected:
```json
{ "connected": false, "message": "Connect Notion by setting NOTION_API_KEY..." }
```
