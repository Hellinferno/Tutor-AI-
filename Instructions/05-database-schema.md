# 05 - Database Schema

Primary database: PostgreSQL. Cache: Redis. Vector store: Qdrant.

## PostgreSQL tables

### users
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| email | text unique | nullable in local demo |
| subject_domain | text | ai_ds, analytics, finance |
| prefs | jsonb | style, privacy, Notion prefs |
| created_at | timestamptz | |

### notebooks
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK | |
| title | text | |
| created_at | timestamptz | |

### sources
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| notebook_id | uuid FK | |
| title | text | |
| kind | enum(pdf, notes, slides, text, other) | |
| status | text | processing, ready, failed |
| text_sha256 | text | dedupe/integrity |
| created_at | timestamptz | |

### source_chunks
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| source_id | uuid FK | |
| notebook_id | uuid FK | filter key |
| chunk_index | int | stable within source |
| text | text | |
| start_char | int | citation offset |
| end_char | int | citation offset |
| vector_id | text | Qdrant point id |

### source_guides
| column | type | notes |
|---|---|---|
| source_id | uuid PK/FK | |
| summary | text | |
| key_concepts | jsonb | |
| suggested_questions | jsonb | |
| created_at | timestamptz | |

### questions
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| canonical_text | text | normalized |
| hash | text unique | cache key |
| subject | text | |
| notebook_id | uuid nullable | if grounded in notebook |
| created_at | timestamptz | |

### solutions
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| question_id | uuid FK | |
| steps | jsonb | reveal-ready |
| answer | text | |
| verify_method | enum(code_exec, symbolic, formula, self_consistency, cross_model, unverified) | |
| verified | bool | |
| citations | jsonb | evidence used |
| created_at | timestamptz | |

### artifacts
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| notebook_id | uuid FK | |
| artifact_type | enum(summary_notes, study_guide, planner, timetable, revision_cards) | |
| title | text | |
| content_markdown | text | export-ready |
| citations | jsonb | |
| notion_page_url | text nullable | |
| created_at | timestamptz | |

### revision_cards
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK | |
| notebook_id | uuid FK | |
| topic | text | |
| due_date | date | |
| interval_days | int | 1/3/7/15/30 |
| state | text | queued, done, lapsed |

## Redis keys
- `sol:{hash}` -> stored solution JSON.
- `sess:{id}` -> live session scratch.

## Qdrant collection
- `source_chunks`
- payload: `notebook_id`, `source_id`, `source_title`, `chunk_index`, `start_char`, `end_char`, `text`
- vectors: dense, sparse, optional late-interaction rerank vector.
