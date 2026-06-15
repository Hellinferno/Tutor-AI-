from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from studylab_core import (
    AuthError,
    QuotaExceededError,
    RateLimitError,
    StudyLabAPI,
    make_rate_limiter_from_env,
    make_store_from_env,
)

VERSION = "0.6.0"

api = StudyLabAPI(make_store_from_env())
RATE_LIMITER = make_rate_limiter_from_env(os.getenv("STUDYLAB_RATE_LIMIT"))
CORS_ORIGINS = os.getenv("STUDYLAB_CORS_ORIGINS", "*")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


# Liveness/readiness + auth endpoints are reachable without a bearer token even when
# auth enforcement is on. NOTE: /metrics is intentionally NOT public — it is gated
# behind auth when STUDYLAB_REQUIRE_AUTH is set.
PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/v1/auth/register",
    "/v1/auth/login",
    "/v1/auth/password/forgot",
    "/v1/auth/password/reset",
}


class StudyLabHandler(BaseHTTPRequestHandler):
    server_version = "StudyLabGateway/0.6"
    auth_user_id: str | None = None

    # ── request entry points ─────────────────────────────────────────────

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self._send_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        self.auth_user_id = None
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok", "version": VERSION})
            return
        if path == "/ready":
            self._json(200, self._readiness())
            return
        if not self._rate_ok():
            return
        if not self._auth_ok(path):
            return
        if path == "/metrics":
            self._handle(lambda: api.metrics_snapshot())
            return
        parts = self._parts(path)
        if len(parts) == 3 and parts[:2] == ["v1", "auth"] and parts[2] == "me":
            self._handle(lambda: api.current_user(self._bearer_token()))
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3] == "sources":
            self._handle(lambda: (self._own(parts[2]), api.get_source(parts[4]))[1])
            return
        if len(parts) == 3 and parts[:2] == ["v1", "teaching"]:
            self._handle(lambda: (self._own_teaching(parts[2]), api.get_teaching_session(session_id=parts[2]))[1])
            return
        if len(parts) == 3 and parts[:2] == ["v1", "quizzes"]:
            include = self._get_query_param("include_answers", "false").lower() == "true"
            self._handle(lambda: (self._own_quiz(parts[2]), api.get_quiz(quiz_id=parts[2], include_answers=include))[1])
            return
        if len(parts) == 3 and parts[:2] == ["v1", "papers"]:
            include = self._get_query_param("include_answers", "false").lower() == "true"
            self._handle(lambda: (self._own_paper(parts[2]), api.get_paper(paper_id=parts[2], include_answers=include))[1])
            return
        if len(parts) == 3 and parts[:2] == ["v1", "reports"]:
            self._handle(lambda: (self._own_attempt(parts[2]), api.get_report(attempt_id=parts[2]))[1])
            return
        # ── Phase 3 GET routes ──
        if len(parts) == 3 and parts[:2] == ["v1", "revision"] and parts[2] == "due":
            self._handle(lambda: api.get_due_cards(user_id=self._uid(self._get_query_param("user_id", "demo-user"))))
            return
        if len(parts) == 3 and parts[:2] == ["v1", "revision"] and parts[2] == "stats":
            self._handle(lambda: api.revision_stats(user_id=self._uid(self._get_query_param("user_id", "demo-user"))))
            return
        if len(parts) == 6 and parts[:2] == ["v1", "student"] and parts[3] == "notebook" and parts[5] == "mastery":
            self._handle(lambda: (self._require_self(parts[2]), self._own(parts[4]), api.get_mastery(user_id=parts[2], notebook_id=parts[4]))[2])
            return
        if len(parts) == 6 and parts[:2] == ["v1", "student"] and parts[3] == "notebook" and parts[5] == "weak-topics":
            self._handle(lambda: (self._require_self(parts[2]), self._own(parts[4]), api.get_weak_topics(user_id=parts[2], notebook_id=parts[4]))[2])
            return
        if len(parts) == 5 and parts[:2] == ["v1", "analytics"] and parts[2] == "notebook" and parts[4] == "trends":
            self._handle(lambda: (self._own(parts[3]), api.notebook_trends(notebook_id=parts[3]))[1])
            return
        if len(parts) == 5 and parts[:2] == ["v1", "analytics"] and parts[2] == "user" and parts[4] == "summary":
            self._handle(lambda: (self._require_self(parts[3]), api.user_summary(user_id=parts[3]))[1])
            return
        # ── Phase 4 GET routes ──
        if len(parts) == 3 and parts[:2] == ["v1", "agent-teaching"]:
            self._handle(lambda: (self._own_agent(parts[2]), api.get_multi_agent_session(session_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "notebooks"] and parts[3] == "imports":
            self._handle(lambda: (self._own(parts[2]), api.list_source_imports(notebook_id=parts[2]))[1])
            return
        if parts == ["v1", "billing", "plans"]:
            self._handle(lambda: api.list_plans())
            return
        if len(parts) == 4 and parts[:2] == ["v1", "billing"] and parts[2] == "subscription":
            self._handle(lambda: (self._require_self(parts[3]), api.get_subscription(user_id=self._uid(parts[3])))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "billing"] and parts[2] == "usage":
            self._handle(lambda: (self._require_self(parts[3]), api.usage_summary(user_id=self._uid(parts[3])))[1])
            return
        # ── Phase 7 GET routes ──
        if parts == ["v1", "notebooks", "shared-with-me"]:
            self._handle(lambda: api.list_shared_with_me(self._session_user()))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "notebooks"] and parts[3] == "shares":
            self._handle(lambda: api.list_shares(self._session_user(), parts[2]))
            return
        if parts == ["v1", "admin", "users"]:
            self._handle(lambda: api.list_users(self._session_user()))
            return
        if parts == ["v1", "admin", "metrics"]:
            self._handle(lambda: (api.require_admin(self._session_user()), api.metrics_snapshot())[1])
            return
        self._json(404, {"error": {"code": "not_found", "message": f"No route for GET {path}"}})

    def do_POST(self) -> None:
        self.auth_user_id = None
        path = urlparse(self.path).path
        if not self._rate_ok():
            return
        if not self._auth_ok(path):
            return
        parts = self._parts(path)
        payload = self._read_json()
        # ── Phase 5/6: Auth + account self-service ──
        if parts == ["v1", "auth", "register"]:
            self._handle(lambda: api.register_user(email=payload["email"], password=payload["password"], subject_domain=payload.get("subject_domain", "ai_ds")))
            return
        if parts == ["v1", "auth", "login"]:
            self._handle(lambda: api.login(email=payload["email"], password=payload["password"]))
            return
        if parts == ["v1", "auth", "password", "forgot"]:
            self._handle(lambda: api.request_password_reset(email=payload["email"]))
            return
        if parts == ["v1", "auth", "password", "reset"]:
            self._handle(lambda: api.reset_password(token=payload["token"], new_password=payload["password"]))
            return
        if parts == ["v1", "auth", "password", "change"]:
            self._handle(lambda: api.change_password(self._token_user_id(), payload["current_password"], payload["new_password"]))
            return
        if parts == ["v1", "auth", "profile"]:
            self._handle(lambda: api.update_profile(self._token_user_id(), subject_domain=payload.get("subject_domain"), prefs=payload.get("prefs")))
            return
        if parts == ["v1", "auth", "delete"]:
            self._handle(lambda: api.delete_account(self._token_user_id()))
            return
        # ── Notebooks / sources ──
        if parts == ["v1", "notebooks"]:
            self._handle(lambda: api.create_notebook(title=payload["title"], user_id=self._uid(payload.get("user_id"))))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "notebooks"] and parts[3] == "ask":
            self._handle(lambda: (self._own(parts[2]), api.ask_notebook(notebook_id=parts[2], query=payload["query"]))[1])
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["sources", "upload"]:
            self._handle(lambda: (self._own(parts[2], edit=True), api.upload_source(notebook_id=parts[2], title=payload["title"], text=payload["text"], kind=payload.get("kind", "notes")))[1])
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["artifacts", "generate"]:
            self._handle(lambda: (self._own(parts[2]), api.generate_artifact(notebook_id=parts[2], artifact_type=payload["artifact_type"], title=payload.get("title")))[1])
            return
        # ── Phase 2: Teaching ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["teaching", "start"]:
            self._handle(lambda: (self._own(parts[2]), api.start_teaching(notebook_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "teaching"] and parts[3] == "next":
            self._handle(lambda: (self._own_teaching(parts[2]), api.teaching_next(session_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "teaching"] and parts[3] == "prev":
            self._handle(lambda: (self._own_teaching(parts[2]), api.teaching_prev(session_id=parts[2]))[1])
            return
        # ── Phase 2: Quizzes ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["quizzes", "generate"]:
            self._handle(lambda: (self._own(parts[2]), api.generate_quiz(notebook_id=parts[2], num_questions=payload.get("num_questions", 5), question_types=payload.get("question_types"), topic=payload.get("topic")))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "quizzes"] and parts[3] == "answer-key":
            self._handle(lambda: (self._own_quiz(parts[2]), api.get_quiz_answer_key(quiz_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "quizzes"] and parts[3] == "attempt":
            self._handle(lambda: (self._own_quiz(parts[2]), api.submit_attempt(source_id=parts[2], source_type="quiz", answers=payload["answers"], user_id=self._uid(payload.get("user_id"))))[1])
            return
        # ── Phase 2: Question Papers ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["papers", "generate"]:
            self._handle(lambda: (self._own(parts[2]), api.generate_paper(notebook_id=parts[2], sections=payload.get("sections"), duration_minutes=payload.get("duration_minutes", 60), topic=payload.get("topic")))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "papers"] and parts[3] == "answer-key":
            self._handle(lambda: (self._own_paper(parts[2]), api.get_paper_answer_key(paper_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "papers"] and parts[3] == "attempt":
            self._handle(lambda: (self._own_paper(parts[2]), api.submit_attempt(source_id=parts[2], source_type="paper", answers=payload["answers"], user_id=self._uid(payload.get("user_id"))))[1])
            return
        # ── Phase 2: Reports ──
        if len(parts) == 4 and parts[:2] == ["v1", "reports"] and parts[3] == "generate":
            self._handle(lambda: (self._own_attempt(parts[2]), api.get_report(attempt_id=parts[2]))[1])
            return
        if parts == ["v1", "solve"]:
            notebook_id = payload.get("notebook_id")
            self._handle(lambda: (self._own(notebook_id) if notebook_id else None, api.solve(content=payload["content"], subject=payload.get("subject", "ai_ds"), input_type=payload.get("input_type", "text"), notebook_id=notebook_id))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "solve"] and parts[3] == "reveal":
            self._handle(lambda: api.reveal(solution_id=parts[2], step_idx=int(payload["step_idx"])))
            return
        if parts == ["v1", "notion", "export"]:
            self._handle(lambda: (self._own_artifact(payload["artifact_id"]), api.export_to_notion(artifact_id=payload["artifact_id"], parent_page_id=payload.get("parent_page_id"), data_source_id=payload.get("data_source_id"), mock=payload.get("mock")))[1])
            return
        # ── Phase 3 POST routes ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["sessions", "start"]:
            self._handle(lambda: (self._own(parts[2]), api.create_session(user_id=self._uid(payload.get("user_id")), notebook_id=parts[2], kind=payload.get("kind", "study")))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "sessions"] and parts[3] == "end":
            self._handle(lambda: (self._own_session(parts[2]), api.end_session(session_id=parts[2]))[1])
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["revision", "generate-cards"]:
            self._handle(lambda: (self._own(parts[2]), api.generate_revision_cards(notebook_id=parts[2], topics=payload.get("topics"), user_id=self._uid(payload.get("user_id")), source=payload.get("source", "manual")))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "revision"] and parts[3] == "review":
            self._handle(lambda: (self._own_card(parts[2]), api.review_card(card_id=parts[2], correct=payload["correct"]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "student"] and parts[3] == "mastery":
            self._handle(lambda: (self._require_self(parts[2]), self._own(payload["notebook_id"]), api.compute_mastery(user_id=parts[2], notebook_id=payload["notebook_id"]))[2])
            return
        if parts == ["v1", "voice", "stt"]:
            self._handle(lambda: api.speech_to_text(audio_base64=payload["audio_base64"], format=payload.get("format", "wav")))
            return
        if parts == ["v1", "voice", "tts"]:
            self._handle(lambda: api.text_to_speech(text=payload["text"], format=payload.get("format", "wav")))
            return
        # ── Phase 4: Multi-agent teaching ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["agent-teaching", "start"]:
            self._handle(lambda: (self._own(parts[2]), api.start_multi_agent_teaching(notebook_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "agent-teaching"] and parts[3] == "next":
            self._handle(lambda: (self._own_agent(parts[2]), api.multi_agent_next(session_id=parts[2]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "agent-teaching"] and parts[3] == "prev":
            self._handle(lambda: (self._own_agent(parts[2]), api.multi_agent_prev(session_id=parts[2]))[1])
            return
        # ── Phase 4: Source connectors ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["sources", "import"]:
            self._handle(lambda: (self._own(parts[2], edit=True), api.import_source(notebook_id=parts[2], connector_type=payload["connector_type"], title=payload.get("title", ""), payload=payload.get("payload", {}), user_id=self._uid(payload.get("user_id"))))[1])
            return
        # ── Phase 4: Billing ──
        if len(parts) == 4 and parts[:2] == ["v1", "billing"] and parts[3] == "subscribe":
            self._handle(lambda: (self._require_self(parts[2]), api.set_plan(user_id=self._uid(parts[2]), tier=payload["tier"]))[1])
            return
        if len(parts) == 4 and parts[:2] == ["v1", "billing"] and parts[3] == "usage":
            self._handle(lambda: (self._require_self(parts[2]), api.record_usage(user_id=self._uid(parts[2]), action=payload["action"], quantity=payload.get("quantity", 1)))[1])
            return
        # ── Phase 7: Sharing ──
        if len(parts) == 4 and parts[:2] == ["v1", "notebooks"] and parts[3] == "shares":
            self._handle(lambda: api.share_notebook(self._session_user(), parts[2], email=payload["email"], role=payload.get("role", "viewer")))
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["shares", "remove"]:
            self._handle(lambda: api.unshare_notebook(self._session_user(), parts[2], share_id=payload["share_id"]))
            return
        self._json(404, {"error": {"code": "not_found", "message": f"No route for POST {path}"}})

    # ── error mapping ────────────────────────────────────────────────────

    def _handle(self, fn):
        try:
            self._json(200, fn())
        except AuthError as exc:
            self._json(401, {"error": {"code": "unauthorized", "message": str(exc)}})
        except PermissionError as exc:
            self._json(403, {"error": {"code": "forbidden", "message": str(exc)}})
        except QuotaExceededError as exc:
            self._json(402, {"error": {"code": "quota_exceeded", "message": str(exc), "quota": exc.detail}})
        except RateLimitError as exc:
            self._json(429, {"error": {"code": "rate_limited", "message": str(exc)}}, extra={"Retry-After": str(exc.retry_after)})
        except KeyError as exc:
            self._json(404, {"error": {"code": "not_found", "message": str(exc)}})
        except (ValueError, IndexError) as exc:
            self._json(400, {"error": {"code": "bad_request", "message": str(exc)}})

    # ── auth / authorization helpers ─────────────────────────────────────

    def _bearer_token(self) -> str:
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header[len("Bearer "):].strip()
        return ""

    def _enforcing(self) -> bool:
        return self.auth_user_id is not None

    def _auth_ok(self, path: str) -> bool:
        """Resolve identity / enforce auth. Sets self.auth_user_id when enforcement is on.

        Default (STUDYLAB_REQUIRE_AUTH unset) keeps the app open for offline/demo use and
        leaves auth_user_id = None, so ownership helpers no-op and writes use the demo user.
        """
        self.auth_user_id = None
        if not _truthy(os.getenv("STUDYLAB_REQUIRE_AUTH")):
            return True
        if path in PUBLIC_PATHS:
            return True
        try:
            self.auth_user_id = api.user_id_from_token(self._bearer_token())
            return True
        except AuthError as exc:
            self._json(401, {"error": {"code": "unauthorized", "message": str(exc)}})
            return False

    def _token_user_id(self) -> str:
        """Resolve the user from the bearer token regardless of enforcement (account routes)."""
        return api.user_id_from_token(self._bearer_token())

    # Phase 7 collaboration/admin routes always act as the logged-in user.
    _session_user = _token_user_id

    def _uid(self, payload_user: str | None = None) -> str:
        return self.auth_user_id if self._enforcing() else (payload_user or "demo-user")

    def _require_self(self, user_id: str) -> None:
        if self._enforcing() and user_id != self.auth_user_id:
            raise PermissionError("you do not have access to this resource")

    def _own(self, notebook_id: str, edit: bool = False) -> None:
        if self._enforcing():
            api.authorize_notebook(self.auth_user_id, notebook_id, require_edit=edit)

    def _own_teaching(self, session_id: str) -> None:
        if self._enforcing():
            self._own(api.notebook_id_for_teaching(session_id))

    def _own_agent(self, session_id: str) -> None:
        if self._enforcing():
            self._own(api.notebook_id_for_agent_session(session_id))

    def _own_quiz(self, quiz_id: str) -> None:
        if self._enforcing():
            self._own(api.store.require_quiz(quiz_id).notebook_id)

    def _own_paper(self, paper_id: str) -> None:
        if self._enforcing():
            self._own(api.store.require_question_paper(paper_id).notebook_id)

    def _own_artifact(self, artifact_id: str) -> None:
        if self._enforcing():
            self._own(api.store.artifacts[artifact_id].notebook_id)

    def _own_attempt(self, attempt_id: str) -> None:
        if self._enforcing():
            self._require_self(api.store.require_attempt(attempt_id).user_id)

    def _own_session(self, session_id: str) -> None:
        if self._enforcing():
            self._require_self(api.store.require_session(session_id).user_id)

    def _own_card(self, card_id: str) -> None:
        if self._enforcing():
            self._require_self(api.store.require_revision_card(card_id).user_id)

    # ── rate limiting + CORS ─────────────────────────────────────────────

    def _rate_ok(self) -> bool:
        if RATE_LIMITER is None:
            return True
        key = self.auth_user_id or self.client_address[0]
        try:
            RATE_LIMITER.check(key)
            return True
        except RateLimitError as exc:
            self._json(429, {"error": {"code": "rate_limited", "message": str(exc)}}, extra={"Retry-After": str(exc.retry_after)})
            return False

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGINS)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")

    def _readiness(self) -> dict[str, Any]:
        # Proves the process is up and the store opened successfully at startup.
        return {"status": "ready", "version": VERSION, "store": type(api.store).__name__}

    # ── plumbing ─────────────────────────────────────────────────────────

    def _parts(self, path: str) -> list[str]:
        return [part for part in path.strip("/").split("/") if part]

    def _get_query_param(self, name: str, default: str = "") -> str:
        from urllib.parse import parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        return params.get(name, [default])[0]

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _json(self, status: int, data: dict[str, Any], extra: dict[str, str] | None = None) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors()
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), StudyLabHandler)
    print(f"StudyLab gateway listening on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
