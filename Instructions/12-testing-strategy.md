# 12 - Testing Strategy

## Test layers
- Unit tests: chunking, retrieval, solver verification, artifact rendering.
- Integration tests: notebook upload -> retrieve -> cited answer -> solve -> reveal -> export.
- Eval gate: checkable solver benchmark and false verified rate.
- E2E smoke: browser flow once JS dependencies are installed.

## RAG tests
- Chunk offsets match source text.
- Source guide has summary, concepts, suggested questions.
- Exact formula terms retrieve through sparse path.
- Conceptual paraphrases retrieve through dense path.
- Reranking selects the best source over distractors.
- Weak retrieval returns insufficient-source-support.
- Citations include source id, title, chunk index, offsets, snippet, score.
- Qdrant adapter payload includes required metadata.

## Solver tests
- Normalization and hash stability.
- Symbolic math pass/fail cases.
- Finance formula cases such as NPV.
- Code sandbox contract and unsafe operation rejection.
- OCR payload enters the same solve path.
- Cached solutions return `from_cache=true`.
- Reveal returns stored steps only.

## Artifact and Notion tests
- Summary notes render from source guides.
- Planner/timetable/revision cards contain notebook concepts.
- Notion mock export returns page URL.
- Missing Notion connection returns clear error.

## Eval metrics
- False verified rate: must be 0.
- Verified-correct rate on seeded checkable cases.
- Retrieval refusal correctness for unsupported questions.
- Citation coverage on grounded answers.
- Latency by path: cache hit, RAG ask, solve.

## Current verification command
```powershell
python -m unittest discover tests
python packages\eval\run_eval.py
python -m compileall packages services
```
