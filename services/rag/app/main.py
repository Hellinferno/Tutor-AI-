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
    # Phase 3: Sessions
    Route("POST", "/v1/notebooks/{notebook_id}/sessions/start", lambda p, b: api.create_session(user_id=b.get("user_id", "demo-user"), notebook_id=p["notebook_id"], kind=b.get("kind", "study"))),
    Route("POST", "/v1/sessions/{session_id}/end", lambda p, b: api.end_session(session_id=p["session_id"])),
    # Phase 3: Revision
    Route(
        "POST", "/v1/notebooks/{notebook_id}/revision/generate-cards",
        lambda p, b: api.generate_revision_cards(notebook_id=p["notebook_id"], topics=b.get("topics"), user_id=b.get("user_id", "demo-user"), source=b.get("source", "manual")),
    ),
    Route("GET", "/v1/revision/due", lambda p, b: api.get_due_cards(user_id="demo-user")),
    Route("GET", "/v1/revision/stats", lambda p, b: api.revision_stats(user_id="demo-user")),
    Route("POST", "/v1/revision/{card_id}/review", lambda p, b: api.review_card(card_id=p["card_id"], correct=b.get("correct", True))),
    # Phase 3: Student
    Route("POST", "/v1/student/{user_id}/mastery", lambda p, b: api.compute_mastery(user_id=p["user_id"], notebook_id=b["notebook_id"])),
    Route("GET", "/v1/student/{user_id}/notebook/{notebook_id}/mastery", lambda p, b: api.get_mastery(user_id=p["user_id"], notebook_id=p["notebook_id"])),
    Route("GET", "/v1/student/{user_id}/notebook/{notebook_id}/weak-topics", lambda p, b: api.get_weak_topics(user_id=p["user_id"], notebook_id=p["notebook_id"])),
    # Phase 3: Analytics
    Route("GET", "/v1/analytics/notebook/{notebook_id}/trends", lambda p, b: api.notebook_trends(notebook_id=p["notebook_id"])),
    Route("GET", "/v1/analytics/user/{user_id}/summary", lambda p, b: api.user_summary(user_id=p["user_id"])),
    # Phase 3: Voice
    Route("POST", "/v1/voice/stt", lambda p, b: api.speech_to_text(audio_base64=b["audio_base64"], format=b.get("format", "wav"))),
    Route("POST", "/v1/voice/tts", lambda p, b: api.text_to_speech(text=b["text"], format=b.get("format", "wav"))),
    # Phase 4: Multi-agent teaching
    Route("POST", "/v1/notebooks/{notebook_id}/agent-teaching/start", lambda p, b: api.start_multi_agent_teaching(notebook_id=p["notebook_id"])),
    Route("GET", "/v1/agent-teaching/{session_id}", lambda p, b: api.get_multi_agent_session(session_id=p["session_id"])),
    Route("POST", "/v1/agent-teaching/{session_id}/next", lambda p, b: api.multi_agent_next(session_id=p["session_id"])),
    Route("POST", "/v1/agent-teaching/{session_id}/prev", lambda p, b: api.multi_agent_prev(session_id=p["session_id"])),
    # Phase 4: Source connectors
    Route(
        "POST", "/v1/notebooks/{notebook_id}/sources/import",
        lambda p, b: api.import_source(notebook_id=p["notebook_id"], connector_type=b["connector_type"], title=b.get("title", ""), payload=b.get("payload", {}), user_id=b.get("user_id", "demo-user")),
    ),
    Route("GET", "/v1/notebooks/{notebook_id}/imports", lambda p, b: api.list_source_imports(notebook_id=p["notebook_id"])),
    # Phase 4: Billing & economics
    Route("GET", "/v1/billing/plans", lambda p, b: api.list_plans()),
    Route("GET", "/v1/billing/subscription/{user_id}", lambda p, b: api.get_subscription(user_id=p["user_id"])),
    Route("GET", "/v1/billing/usage/{user_id}", lambda p, b: api.usage_summary(user_id=p["user_id"])),
    Route("POST", "/v1/billing/{user_id}/subscribe", lambda p, b: api.set_plan(user_id=p["user_id"], tier=b["tier"])),
    Route("POST", "/v1/billing/{user_id}/usage", lambda p, b: api.record_usage(user_id=p["user_id"], action=b["action"], quantity=b.get("quantity", 1))),
    # Phase 5: Auth & observability
    Route("POST", "/v1/auth/register", lambda p, b: api.register_user(email=b["email"], password=b["password"], subject_domain=b.get("subject_domain", "ai_ds"))),
    Route("POST", "/v1/auth/login", lambda p, b: api.login(email=b["email"], password=b["password"])),
    Route("GET", "/metrics", lambda p, b: api.metrics_snapshot()),
]


def main() -> None:
    serve("StudyLabRag/0.1", ROUTES, env_port="RAG_PORT", default_port=8001)


if __name__ == "__main__":
    main()
