"""A local mesh viewer and editor, served to the browser.

Runs on the standard library's HTTP server and binds to the loopback interface
by default: this is a local tool, not a service.  The same page is intended to
become the static, WebAssembly-hosted build later, so it talks to a small JSON
API and holds no server-side session state beyond the open document.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from candejar.io import Line, Record, dumps, read_cid, write_cid
from candejar.model import Problem
from candejar.report import summary_rows, uncatalogued
from candejar.validate import run_rules

__all__ = ["payload_for", "serve"]

_STATIC = Path(__file__).parent / "static"


def payload_for(problem: Problem, path: Path | None) -> dict[str, Any]:
    """Everything the page needs to draw and explain the model."""
    extents = problem.extents
    return {
        "path": str(path) if path else None,
        "name": path.name if path else "untitled",
        "title": problem.title,
        "summary": [{"label": label, "value": value} for label, value in summary_rows(problem)],
        "level": problem.level,
        "hasMesh": problem.has_mesh,
        "loadSteps": problem.load_steps,
        "loadScaling": problem.load_scaling,
        "extents": (
            {
                "minX": extents.min_x,
                "minY": extents.min_y,
                "maxX": extents.max_x,
                "maxY": extents.max_y,
            }
            if extents
            else None
        ),
        "nodes": {str(n.number): [n.x, n.y] for n in problem.nodes.values()},
        "elements": [
            {
                "n": e.number,
                "nodes": list(e.nodes),
                "kind": e.kind.value,
                "material": e.material,
                "birth": e.birth,
                "code": e.code,
                "index": e.index,
            }
            for e in problem.elements.values()
        ],
        "materials": [
            {
                "number": m.number,
                "model": m.model,
                "kind": m.kind.label if m.kind else f"model {m.model}",
                "isInterface": m.is_interface,
                "density": m.density,
                "name": m.name,
                "index": m.index,
            }
            for m in problem.materials
        ],
        "boundaries": [
            {
                "node": b.node,
                "xCode": b.x_code,
                "xValue": b.x_value,
                "yCode": b.y_code,
                "yValue": b.y_value,
                "step": b.step,
                "index": b.index,
                "isLoad": b.is_load,
            }
            for b in problem.boundaries
        ],
        "steps": list(problem.steps()),
        "findings": [
            {
                "rule": f.rule,
                "severity": f.severity.value,
                "message": f.message,
                "entity": f.entity,
                "index": f.index,
                "hint": f.hint,
            }
            for f in run_rules(problem)
        ],
        "uncatalogued": uncatalogued(problem),
    }


@dataclass
class _Session:
    """The document currently open, and where it came from."""

    problem: Problem | None = None
    path: Path | None = None
    dirty: bool = False

    def load(self, path: Path) -> None:
        self.problem = Problem(read_cid(path))
        self.path = path
        self.dirty = False

    def load_text(self, text: str, name: str) -> None:
        from candejar.io import loads

        self.problem = Problem(loads(text))
        self.path = Path(name)
        self.dirty = True

    def apply(self, edits: list[dict[str, Any]]) -> int:
        """Apply field edits by document line index. Returns the number applied."""
        if self.problem is None:
            return 0
        document = self.problem.document
        changes: dict[int, Line] = {}
        for edit in edits:
            index = int(edit["index"])
            line = document.lines[index]
            if not isinstance(line, Record):
                continue
            changes[index] = line.set(str(edit["field"]), edit["value"])
        if not changes:
            return 0
        self.problem = Problem(document.with_changes(changes))
        self.dirty = True
        return len(changes)


class _Handler(BaseHTTPRequestHandler):
    session: _Session
    server_version = "candejar"

    def log_message(self, format: str, *args: Any) -> None:
        pass  # a local tool has no use for an access log

    # ------------------------------------------------------------- plumbing
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: object, status: int = 200) -> None:
        self._send(status, json.dumps(data).encode("utf-8"), "application/json")

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _state(self) -> dict[str, Any]:
        if self.session.problem is None:
            return {"open": False}
        data = payload_for(self.session.problem, self.session.path)
        data["open"] = True
        data["dirty"] = self.session.dirty
        return data

    # ------------------------------------------------------------- requests
    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, (_STATIC / "app.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        elif self.path == "/api/state":
            self._send_json(self._state())
        elif self.path == "/api/text":
            if self.session.problem is None:
                self._send_json({"error": "nothing open"}, 404)
            else:
                self._send(
                    200,
                    dumps(self.session.problem.document).encode("latin-1"),
                    "text/plain; charset=latin-1",
                )
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/open":
                body = self._read_json()
                self.session.load_text(body["text"], body.get("name", "dropped.cid"))
                self._send_json(self._state())
            elif self.path == "/api/edit":
                applied = self.session.apply(self._read_json().get("edits", []))
                state = self._state()
                state["applied"] = applied
                self._send_json(state)
            elif self.path == "/api/save":
                self._save(self._read_json())
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as error:  # a local tool should say what went wrong
            self._send_json({"error": f"{type(error).__name__}: {error}"}, 400)

    def _save(self, body: dict[str, Any]) -> None:
        if self.session.problem is None:
            self._send_json({"error": "nothing open"}, 400)
            return
        target = Path(body.get("path") or self.session.path or "untitled.cid")
        write_cid(self.session.problem.document, target)
        self.session.path = target
        self.session.dirty = False
        self._send_json({"saved": str(target)})


def serve(
    file: Path | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8737,
    open_browser: bool = True,
) -> None:
    """Serve the viewer until interrupted."""
    session = _Session()
    if file is not None:
        session.load(Path(file))

    handler = type("Handler", (_Handler,), {"session": session})
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"

    opened = session.path.name if session.path else "no file"
    print(f"candejar viewer  {url}   ({opened})")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
