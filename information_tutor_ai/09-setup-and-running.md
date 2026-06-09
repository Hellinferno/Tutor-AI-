# 09 — Setup & Running 🔵

How to get the project running locally. Two tracks: **Python backend** and **web frontend**.

> 🟢 **Plain English:** this is the "install and start" guide. The backend (the brains) needs
> Python; the website needs Node.js. You can run either on its own.

---

## Prerequisites

| Tool | Version | For |
|---|---|---|
| Python | ≥ 3.11 | the engine, services, tests, eval |
| Node.js | ≥ 18 (tested on 24) | the web app |
| npm | bundled with Node | installing web deps (pnpm also fine if available) |
| Docker (optional) | recent | running the full stack via compose |

No external services or API keys are needed to run and test the core — it's self‑contained.

---

## Backend: run the engine, services, tests

From the repository root (`tutor AI/`):

```powershell
# Make the core importable (PowerShell)
$env:PYTHONPATH = "packages/studylab_core"

# Run the full test suite (24 tests)
python -m unittest discover tests

# Run the solver quality gate (must report false_verified_rate=0)
python packages/eval/run_eval.py
```

### Start a service
```powershell
# In-memory (ephemeral)
python -m services.gateway.app.main          # http://localhost:8000

# Durable local persistence
$env:STUDYLAB_SQLITE_PATH = "data/studylab.db"
python -m services.gateway.app.main

# The other two services
python -m services.rag.app.main              # http://localhost:8001  (RAG_PORT)
python -m services.solver.app.main           # http://localhost:8002  (SOLVER_PORT)
```

### Smoke test with curl
```powershell
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/notebooks -H "Content-Type: application/json" -d '{"title":"ML Notes"}'
curl -X POST http://localhost:8000/v1/solve -H "Content-Type: application/json" -d '{"content":"What is 2 + 2 * 3?","subject":"analytics"}'
```

---

## Frontend: build/run the web app

```powershell
cd apps/web
npm install
npm run build      # production build (compiles, type-checks, prerenders)
npm run dev        # local dev server
```
`node_modules/` and `.next/` are git‑ignored.

---

## Full stack with Docker Compose

```powershell
docker compose -f infra/compose/docker-compose.yml up --build
```
Brings up **postgres, redis, qdrant, gateway, rag, solver** with a shared `studylab_data` volume
so all three services read/write the same SQLite DB (`/data/studylab.db`). Ports: gateway `8000`,
rag `8001`, solver `8002`.

---

## Environment variables

All documented in [.env.example](../.env.example). The ones that change behaviour today:

| Variable | Effect |
|---|---|
| `STUDYLAB_SQLITE_PATH` | Set → durable SQLite; unset → in‑memory. |
| `PORT` / `RAG_PORT` / `SOLVER_PORT` | Service ports (8000 / 8001 / 8002). |
| `STUDYLAB_PROMPTS_DIR` | Override where prompt templates are loaded from. |
| `NOTION_MOCK_EXPORT` | `true` → mock Notion export for demos. |
| `NOTION_API_KEY` | Set → real Notion export. |

Variables present for the **production target** but not yet the live path: `DATABASE_URL`
(Postgres), `QDRANT_URL`/`QDRANT_COLLECTION`, `REDIS_URL`, `EMBEDDINGS_ENDPOINT`. See
[11-current-status.md](11-current-status.md).
