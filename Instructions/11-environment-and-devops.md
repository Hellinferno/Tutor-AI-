# 11 - Environment and DevOps

## Environments
- **Local**: Python core, gateway, static/Next web, Postgres, Redis, Qdrant, sandbox.
- **Staging**: full stack with seeded notebooks and sample sources.
- **Production**: same architecture, with managed Postgres/Redis and production vector service.

## Required services
- Postgres for product metadata.
- Redis for solution cache.
- Qdrant for hybrid source chunk retrieval.
- Code sandbox for execution checks.
- Notion API for artifact export.
- Optional frontier API for hard/non-verifiable tail.

## Env vars
```text
DATABASE_URL=
REDIS_URL=
QDRANT_URL=
QDRANT_COLLECTION=source_chunks
RAG_RETRIEVER=local_hybrid
RAG_TOP_K=4
RAG_CANDIDATE_K=40
RAG_MIN_SCORE=0.16
FRONTIER_API_KEY=
OPENWEIGHT_ENDPOINT=
EMBEDDINGS_ENDPOINT=
SANDBOX_ENDPOINT=
NOTION_API_KEY=
NOTION_MOCK_EXPORT=true
CACHE_TTL=
```

## CI/CD
- PR: unit tests -> solver eval -> manifest validation -> frontend typecheck/build when dependencies are installed.
- Merge: build images -> deploy staging -> smoke test notebook upload/ask/solve/export.

## Observability
- Retrieval score distribution.
- Weak retrieval refusal rate.
- Citation coverage rate.
- Verified rate and false verified rate.
- Solve latency p50/p90/p99.
- Cache hit rate.
- Notion export success/failure.
- Sandbox timeout/failure rate.

## Security notes
- Uploaded source content is private per user.
- Frontier and Notion keys are server-side only.
- Sandbox must run without network and with hard time/memory limits.
