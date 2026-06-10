from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from studylab_core import StudyLabAPI, make_store_from_env


api = StudyLabAPI(make_store_from_env())


class StudyLabHandler(BaseHTTPRequestHandler):
    server_version = "StudyLabGateway/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok"})
            return
        parts = self._parts(path)
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3] == "sources":
            self._handle(lambda: api.get_source(parts[4]))
            return
        if len(parts) == 3 and parts[:2] == ["v1", "teaching"]:
            self._handle(lambda: api.get_teaching_session(session_id=parts[2]))
            return
        if len(parts) == 3 and parts[:2] == ["v1", "quizzes"]:
            include = self._get_query_param("include_answers", "false").lower() == "true"
            self._handle(lambda: api.get_quiz(quiz_id=parts[2], include_answers=include))
            return
        if len(parts) == 3 and parts[:2] == ["v1", "papers"]:
            include = self._get_query_param("include_answers", "false").lower() == "true"
            self._handle(lambda: api.get_paper(paper_id=parts[2], include_answers=include))
            return
        if len(parts) == 3 and parts[:2] == ["v1", "reports"]:
            self._handle(lambda: api.get_report(attempt_id=parts[2]))
            return
        self._json(404, {"error": {"code": "not_found", "message": f"No route for GET {path}"}})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        parts = self._parts(path)
        payload = self._read_json()
        if parts == ["v1", "notebooks"]:
            self._handle(lambda: api.create_notebook(title=payload["title"], user_id=payload.get("user_id", "demo-user")))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "notebooks"] and parts[3] == "ask":
            self._handle(lambda: api.ask_notebook(notebook_id=parts[2], query=payload["query"]))
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["sources", "upload"]:
            self._handle(
                lambda: api.upload_source(
                    notebook_id=parts[2],
                    title=payload["title"],
                    text=payload["text"],
                    kind=payload.get("kind", "notes"),
                )
            )
            return
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["artifacts", "generate"]:
            self._handle(
                lambda: api.generate_artifact(
                    notebook_id=parts[2],
                    artifact_type=payload["artifact_type"],
                    title=payload.get("title"),
                )
            )
            return
        # ── Phase 2: Teaching ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["teaching", "start"]:
            self._handle(lambda: api.start_teaching(notebook_id=parts[2]))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "teaching"] and parts[3] == "next":
            self._handle(lambda: api.teaching_next(session_id=parts[2]))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "teaching"] and parts[3] == "prev":
            self._handle(lambda: api.teaching_prev(session_id=parts[2]))
            return
        # ── Phase 2: Quizzes ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["quizzes", "generate"]:
            self._handle(
                lambda: api.generate_quiz(
                    notebook_id=parts[2],
                    num_questions=payload.get("num_questions", 5),
                    question_types=payload.get("question_types"),
                    topic=payload.get("topic"),
                )
            )
            return
        if len(parts) == 4 and parts[:2] == ["v1", "quizzes"] and parts[3] == "answer-key":
            self._handle(lambda: api.get_quiz_answer_key(quiz_id=parts[2]))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "quizzes"] and parts[3] == "attempt":
            self._handle(
                lambda: api.submit_attempt(
                    source_id=parts[2], source_type="quiz",
                    answers=payload["answers"], user_id=payload.get("user_id", "demo-user"),
                )
            )
            return
        # ── Phase 2: Question Papers ──
        if len(parts) == 5 and parts[:2] == ["v1", "notebooks"] and parts[3:] == ["papers", "generate"]:
            self._handle(
                lambda: api.generate_paper(
                    notebook_id=parts[2],
                    sections=payload.get("sections"),
                    duration_minutes=payload.get("duration_minutes", 60),
                    topic=payload.get("topic"),
                )
            )
            return
        if len(parts) == 4 and parts[:2] == ["v1", "papers"] and parts[3] == "answer-key":
            self._handle(lambda: api.get_paper_answer_key(paper_id=parts[2]))
            return
        if len(parts) == 4 and parts[:2] == ["v1", "papers"] and parts[3] == "attempt":
            self._handle(
                lambda: api.submit_attempt(
                    source_id=parts[2], source_type="paper",
                    answers=payload["answers"], user_id=payload.get("user_id", "demo-user"),
                )
            )
            return
        # ── Phase 2: Reports ──
        if len(parts) == 4 and parts[:2] == ["v1", "reports"] and parts[3] == "generate":
            self._handle(lambda: api.get_report(attempt_id=parts[2]))
            return
        if parts == ["v1", "solve"]:
            self._handle(
                lambda: api.solve(
                    content=payload["content"],
                    subject=payload.get("subject", "ai_ds"),
                    input_type=payload.get("input_type", "text"),
                    notebook_id=payload.get("notebook_id"),
                )
            )
            return
        if len(parts) == 4 and parts[:2] == ["v1", "solve"] and parts[3] == "reveal":
            self._handle(lambda: api.reveal(solution_id=parts[2], step_idx=int(payload["step_idx"])))
            return
        if parts == ["v1", "notion", "export"]:
            self._handle(
                lambda: api.export_to_notion(
                    artifact_id=payload["artifact_id"],
                    parent_page_id=payload.get("parent_page_id"),
                    data_source_id=payload.get("data_source_id"),
                    mock=payload.get("mock"),
                )
            )
            return
        self._json(404, {"error": {"code": "not_found", "message": f"No route for POST {path}"}})

    def _handle(self, fn):
        try:
            self._json(200, fn())
        except KeyError as exc:
            self._json(404, {"error": {"code": "not_found", "message": str(exc)}})
        except (ValueError, IndexError) as exc:
            self._json(400, {"error": {"code": "bad_request", "message": str(exc)}})

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

    def _json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), StudyLabHandler)
    print(f"StudyLab gateway listening on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
