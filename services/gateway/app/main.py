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
