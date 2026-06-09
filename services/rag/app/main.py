from __future__ import annotations

from studylab_core import InMemoryStudyLabStore, RagEngine, StudyLabAPI, make_store_from_env
from studylab_core.service_http import Route, serve


def create_rag_engine() -> RagEngine:
    return RagEngine(InMemoryStudyLabStore())


api = StudyLabAPI(make_store_from_env())


ROUTES = [
    Route("POST", "/v1/notebooks", lambda p, b: api.create_notebook(title=b["title"], user_id=b.get("user_id", "demo-user"))),
    Route(
        "POST",
        "/v1/notebooks/{notebook_id}/sources/upload",
        lambda p, b: api.upload_source(
            notebook_id=p["notebook_id"], title=b["title"], text=b["text"], kind=b.get("kind", "notes")
        ),
    ),
    Route("GET", "/v1/notebooks/{notebook_id}/sources/{source_id}", lambda p, b: api.get_source(p["source_id"])),
    Route("POST", "/v1/notebooks/{notebook_id}/ask", lambda p, b: api.ask_notebook(notebook_id=p["notebook_id"], query=b["query"])),
    Route(
        "POST",
        "/v1/notebooks/{notebook_id}/artifacts/generate",
        lambda p, b: api.generate_artifact(
            notebook_id=p["notebook_id"], artifact_type=b["artifact_type"], title=b.get("title")
        ),
    ),
]


def main() -> None:
    serve("StudyLabRag/0.1", ROUTES, env_port="RAG_PORT", default_port=8001)


if __name__ == "__main__":
    main()
