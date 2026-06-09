# Project Build-Readiness Plan

Scaling, pricing, and GTM are deferred. This checklist focuses on readiness for a working build.

## Target users
- AI, data science, and analytics students.
- Finance students.

## What ready means
A user can create a notebook, upload source material, receive a source guide, ask cited questions, solve checkable problems with verification, generate study artifacts, and export those artifacts to Notion.

## Readiness checklist

### Notebook and RAG
- [ ] Notebook creation works.
- [ ] Source upload works for notes/text and PDF-extracted text.
- [ ] Chunk offsets are stable.
- [ ] Source guides are generated.
- [ ] Dense + sparse hybrid retrieval works.
- [ ] Reranking selects the best evidence.
- [ ] Weak retrieval refuses grounding.
- [ ] Cited answers include source id, title, chunk index, offsets, snippet, score.

### Verified solver
- [ ] Normalization/hash cache works.
- [ ] Symbolic/math checks pass known cases.
- [ ] Finance formula checks pass NPV and later IRR/TVM/ratios.
- [ ] Code sandbox contract exists.
- [ ] Reveal reads stored steps only.
- [ ] False verified rate is 0 on benchmark.

### Artifacts and Notion
- [ ] Summary notes generate from notebook sources.
- [ ] Study guides generate from source guides.
- [ ] Planner and timetable generate from concepts.
- [ ] Revision cards generate from concepts.
- [ ] Notion mock export works locally.
- [ ] Real Notion export works when connected.

### Platform
- [ ] Local Docker Compose has Postgres, Redis, Qdrant, gateway, sandbox.
- [ ] CircleCI runs tests and eval.
- [ ] Env vars documented.
- [ ] Secrets remain server-side.

## Metrics to watch
- Citation coverage.
- Weak retrieval refusal rate.
- Retrieval score distribution.
- Verified rate.
- False verified rate.
- Solve latency.
- Cache hit rate.
- Notion export success rate.

## Deferred
- Pricing, COGS, margins.
- Acquisition/GTM.
- Full scale optimization.
- Mobile.
- Multi-agent system.
