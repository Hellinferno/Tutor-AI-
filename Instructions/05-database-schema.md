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

### whiteboard_sessions
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| notebook_id | uuid FK | |
| current_concept_idx | int | current teaching concept |
| concept_progression | jsonb | ordered whiteboard concepts |
| completed | bool | |
| created_at | timestamptz | |

### quizzes
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| notebook_id | uuid FK | |
| title | text | |
| topic | text nullable | optional topic hint |
| num_questions | int | |
| created_at | timestamptz | |

### quiz_questions
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| quiz_id | uuid FK | |
| type | enum(mcq, true_false, short_answer) | |
| question_text | text | |
| options | jsonb | |
| correct_answer | text | hidden unless answer key requested |
| points | int | |
| difficulty | enum(easy, medium, hard) | |
| citations | jsonb | |
| idx | int | stable ordering |

### question_papers
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| notebook_id | uuid FK | |
| title | text | |
| total_marks | int | |
| duration_minutes | int | |
| created_at | timestamptz | |

### paper_sections
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| paper_id | uuid FK | |
| title | text | |
| instructions | text | |
| idx | int | stable ordering |

### answer_keys
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| source_id | uuid | quiz_id or paper_id |
| source_type | enum(quiz, paper) | |
| answers | jsonb | includes per-answer verified and verification_method |
| verified | bool | all answer keys passed deterministic checks |
| verification_method | text | key-level verification method |
| generated_at | timestamptz | |

### attempts
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| source_id | uuid | quiz_id or paper_id |
| source_type | enum(quiz, paper) | |
| user_id | uuid FK | |
| answers | jsonb | scored answers |
| total_score | float | |
| max_score | float | |
| completed_at | timestamptz | |

### eval_reports
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| attempt_id | uuid FK | |
| total_score | float | |
| max_score | float | |
| percentage | float | |
| per_question | jsonb | |
| weak_topics | jsonb | |
| strong_topics | jsonb | |
| summary | text | |
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
