from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse


# A handler receives (path_params, json_payload) and returns a JSON-able dict.
Handler = Callable[[dict[str, str], dict[str, Any]], Any]


class Route:
    def __init__(self, method: str, pattern: str, handler: Handler) -> None:
        self.method = method.upper()
        self.parts = [part for part in pattern.strip("/").split("/") if part]
        self.handler = handler

    def match(self, method: str, path_parts: list[str]) -> dict[str, str] | None:
        if method != self.method or len(path_parts) != len(self.parts):
            return None
        params: dict[str, str] = {}
        for template, actual in zip(self.parts, path_parts):
            if template.startswith("{") and template.endswith("}"):
                params[template[1:-1]] = actual
            elif template != actual:
                return None
        return params


def build_handler_class(server_name: str, routes: list[Route]) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        server_version = server_name

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            self._dispatch("POST")

        def _dispatch(self, method: str) -> None:
            path = urlparse(self.path).path
            parts = [part for part in path.strip("/").split("/") if part]
            if method == "GET" and path == "/health":
                self._json(200, {"status": "ok", "service": server_name})
                return
            payload = self._read_json()
            for route in routes:
                params = route.match(method, parts)
                if params is None:
                    continue
                try:
                    self._json(200, route.handler(params, payload))
                except KeyError as exc:
                    self._json(404, {"error": {"code": "not_found", "message": str(exc)}})
                except (ValueError, IndexError) as exc:
                    self._json(400, {"error": {"code": "bad_request", "message": str(exc)}})
                return
            self._json(404, {"error": {"code": "not_found", "message": f"No route for {method} {path}"}})

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _json(self, status: int, data: Any) -> None:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: Any) -> None:  # quiet by default
            pass

    return _Handler


def serve(server_name: str, routes: list[Route], env_port: str, default_port: int, host: str | None = None) -> None:
    port = int(os.getenv(env_port, str(default_port)))
    bind_host = host or os.getenv("BIND_HOST", "0.0.0.0")
    handler_class = build_handler_class(server_name, routes)
    server = ThreadingHTTPServer((bind_host, port), handler_class)
    print(f"{server_name} listening on http://{bind_host}:{port}")
    server.serve_forever()
