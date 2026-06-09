# Tutor‑AI — Project Information Hub

This folder is the **single place to understand the Tutor‑AI project**. It is written in two
layers so both audiences are served:

- 🟢 **For everyone** — plain‑English explainers, no coding knowledge needed.
- 🔵 **For developers** — precise technical references that match the actual code.

Every document reflects the **current state of the repository** (not a future plan). When the
code changes, these documents should be updated to match.

---

## Start here

| If you are… | Read this first |
|---|---|
| Curious what this product *is* | [01-what-is-tutor-ai.md](01-what-is-tutor-ai.md) 🟢 |
| A developer joining the project | [02-architecture.md](02-architecture.md) → [03-codebase-map.md](03-codebase-map.md) 🔵 |
| Setting it up on your machine | [09-setup-and-running.md](09-setup-and-running.md) 🔵 |
| Checking what's done vs. stubbed | [11-current-status.md](11-current-status.md) 🟢🔵 |
| Confused by a term | [12-glossary.md](12-glossary.md) 🟢 |

---

## Table of contents

1. [What is Tutor‑AI?](01-what-is-tutor-ai.md) — 🟢 the product in plain English
2. [Architecture](02-architecture.md) — 🔵 services, components, and how a request flows
3. [Codebase map](03-codebase-map.md) — 🔵 every folder and file, explained
4. [Data model](04-data-model.md) — 🔵 database tables and what they store
5. [API reference](05-api-reference.md) — 🔵 every HTTP endpoint
6. [RAG & retrieval](06-rag-and-retrieval.md) — 🟢🔵 how grounded answers + citations work
7. [Verified solver & sandbox](07-solver-and-sandbox.md) — 🟢🔵 how answers get *verified*
8. [Persistence](08-persistence.md) — 🔵 in‑memory vs. SQLite vs. Postgres
9. [Setup & running](09-setup-and-running.md) — 🔵 install, run, Docker
10. [Testing & evaluation](10-testing-and-eval.md) — 🔵 the quality gate
11. [Current status](11-current-status.md) — 🟢🔵 what's real, what's a stub
12. [Glossary](12-glossary.md) — 🟢 jargon decoder

---

## The one‑paragraph summary

Tutor‑AI is a **NotebookLM‑inspired study assistant** for AI, data‑science, analytics, and
finance learners. You upload your own study material into a "notebook," and the app answers
your questions **using only those sources** (with citations), refuses to answer when it lacks
support, **solves math/finance/coding problems and verifies the answers**, and generates study
artifacts (summary notes, study guides, planners, revision cards) that can be exported to
Notion. This repository contains the **Phase 0 + Phase 1 vertical slice**: a working,
fully‑tested core that runs without any external cloud services.

> 🟢 **Non‑developer note:** "Phase 0 + Phase 1" just means *the foundation and the first
> complete feature set*. Later phases (teaching with a whiteboard, quizzes, memory/revision,
> voice) are planned but not built yet. See [11-current-status.md](11-current-status.md).
