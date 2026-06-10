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
    # Phase 2: Teaching
    Route("POST", "/v1/notebooks/{notebook_id}/teaching/start", lambda p, b: api.start_teaching(notebook_id=p["notebook_id"])),
    Route("GET", "/v1/teaching/{session_id}", lambda p, b: api.get_teaching_session(session_id=p["session_id"])),
    Route("POST", "/v1/teaching/{session_id}/next", lambda p, b: api.teaching_next(session_id=p["session_id"])),
    Route("POST", "/v1/teaching/{session_id}/prev", lambda p, b: api.teaching_prev(session_id=p["session_id"])),
    # Phase 2: Quizzes
    Route(
        "POST",
        "/v1/notebooks/{notebook_id}/quizzes/generate",
        lambda p, b: api.generate_quiz(
            notebook_id=p["notebook_id"],
            num_questions=b.get("num_questions", 5),
            question_types=b.get("question_types"),
            topic=b.get("topic"),
        ),
    ),
    Route("GET", "/v1/quizzes/{quiz_id}", lambda p, b: api.get_quiz(quiz_id=p["quiz_id"], include_answers=False)),
    Route("GET", "/v1/quizzes/{quiz_id}/answer-key", lambda p, b: api.get_quiz_answer_key(quiz_id=p["quiz_id"])),
    Route(
        "POST", "/v1/quizzes/{quiz_id}/attempt",
        lambda p, b: api.submit_attempt(source_id=p["quiz_id"], source_type="quiz", answers=b["answers"], user_id=b.get("user_id", "demo-user")),
    ),
    # Phase 2: Papers
    Route(
        "POST",
        "/v1/notebooks/{notebook_id}/papers/generate",
        lambda p, b: api.generate_paper(
            notebook_id=p["notebook_id"],
            sections=b.get("sections"),
            duration_minutes=b.get("duration_minutes", 60),
        ),
    ),
    Route("GET", "/v1/papers/{paper_id}", lambda p, b: api.get_paper(paper_id=p["paper_id"], include_answers=False)),
    Route("GET", "/v1/papers/{paper_id}/answer-key", lambda p, b: api.get_paper_answer_key(paper_id=p["paper_id"])),
    Route(
        "POST", "/v1/papers/{paper_id}/attempt",
        lambda p, b: api.submit_attempt(source_id=p["paper_id"], source_type="paper", answers=b["answers"], user_id=b.get("user_id", "demo-user")),
    ),
    # Phase 2: Reports
    Route("GET", "/v1/reports/{attempt_id}", lambda p, b: api.get_report(attempt_id=p["attempt_id"])),
]


def main() -> None:
    serve("StudyLabRag/0.1", ROUTES, env_port="RAG_PORT", default_port=8001)


if __name__ == "__main__":
    main()
