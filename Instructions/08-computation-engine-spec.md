# 08 - Computation Engine Spec

The computation engine combines hybrid RAG, verified solving, and stored step reveal.

## RAG engine

### Goal
Return source-grounded answers with citations when evidence is strong, and refuse grounding when evidence is weak.

### Retrieval stages
1. Notebook filter: search only the selected notebook by default.
2. Sparse retrieval: exact terms, formulas, finance labels, code identifiers.
3. Dense retrieval: semantic/paraphrase match.
4. Candidate merge: combine dense and sparse candidates.
5. Rerank: prefer phrase/proximity/formula matches and stronger evidence.
6. Citation output: source id, title, chunk index, offsets, snippet, score.

### Low confidence policy
If no candidate passes the threshold, return `insufficient_source_support`. Do not answer as if grounded.

## Solver engine

### Pipeline
```text
question
-> normalize + hash
-> cache lookup
-> optional notebook retrieval
-> solve
-> verify
-> store answer and steps
-> return response
```

### Verification
- Code: isolated sandbox execution.
- Math/stats: symbolic or numeric check.
- Finance: formula evaluation.
- Conceptual: unverified unless cross-check passes.

### Cache
- Key: normalized question hash.
- Value: answer, steps, verification method, citations.

### Step reveal
Stored solution steps are revealed by index. The reveal route must not call a model or recompute the solution.

## Artifact engine
Generates markdown artifacts from notebook source guides and cited chunks:
- summary notes
- study guide
- planner
- timetable
- revision cards

## Notion export engine
Renders artifact markdown into Notion blocks and creates a private page by default. If Notion is not connected, return a clear connection error.

## Quality gates
- False verified rate must be zero on seeded checkable cases.
- Weak retrieval must not produce grounded answers.
- Cited answers must include source metadata and snippet.
- Solver eval must pass before prompt/model changes merge.
