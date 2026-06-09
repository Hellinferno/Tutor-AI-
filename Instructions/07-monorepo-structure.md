# 07 - Monorepo Structure

Tooling: pnpm workspaces and Turborepo for web/packages, Python for core services.

```text
studylab/
|-- apps/
|   |-- web/                         # Next.js UI and static preview
|       |-- app/
|       |-- components/
|       |-- lib/
|       |-- preview.html
|-- services/
|   |-- gateway/                     # HTTP API gateway
|   |-- rag/                         # RAG service wrapper
|   |-- solver/                      # Solver service wrapper
|-- packages/
|   |-- studylab_core/               # dependency-light Phase 1 core
|   |   |-- rag.py
|   |   |-- retrieval.py             # hybrid retrieval + Qdrant adapter
|   |   |-- solver.py
|   |   |-- artifacts.py
|   |   |-- notion.py
|   |-- db/
|   |   |-- migrations/
|   |-- shared-types/
|   |-- eval/
|   |   |-- benchmarks/
|   |-- prompts/
|-- infra/
|   |-- compose/
|   |-- docker/
|-- data/
|   |-- fixtures/
|   |-- concept-bank/
|-- docs/
|-- files/                           # product/spec source of truth
|-- tests/
|-- .circleci/
```

## Boundaries
- `packages/studylab_core` holds local, testable product logic.
- `services/gateway` exposes `/v1` API routes.
- `services/rag` and `services/solver` are deployment wrappers around core engines.
- `apps/web` is the user interface.
- `packages/db` owns migrations.
- `packages/eval` owns benchmark gates.

## Current local implementation
- Uses in-memory store before Postgres/Redis/Qdrant are provisioned.
- Uses deterministic local embeddings before production embedding service is connected.
- Includes Qdrant adapter contract for production hybrid retrieval.
- Includes Notion API adapter plus mock mode.

## CI
CircleCI runs Python tests, solver eval gate, and manifest validation. Later CI should add frontend typecheck/build once JS dependencies are installed.
