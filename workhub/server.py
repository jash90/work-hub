"""The HTTP layer: stdlib only, bound to the loopback interface.

The hub has exactly one route that changes anything outside this machine
(POST /api/tempo/log). That single fact drives the guards here: loopback-only bind, a Host
check so a hostile page cannot reach us by DNS rebinding, and a start-up CSRF token that
every POST must echo.
"""
import json
import os
import secrets
import socket
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import DATA_DIR, render, sources, store
from .runner import Runner
from .scheduler import Scheduler

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
LOOPBACK = {"localhost", "127.0.0.1", "[::1]", "::1"}
CONTENT_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}


class Hub:
    """Everything the handler needs, built once and shared by every request thread."""

    def __init__(self):
        self.csrf = secrets.token_urlsafe(24)
        self.runner = Runner()
        self.scheduler = Scheduler(self.runner)


class Handler(BaseHTTPRequestHandler):
    server_version = "work-hub"
    hub = None

    def log_message(self, fmt, *args):
        pass

    # ---------- plumbing ----------

    def _send(self, code, body, content_type="text/html; charset=utf-8"):
        blob = body.encode("utf-8") if isinstance(body, str) else body

        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(blob)

    def _json(self, code, data):
        self._send(code, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")

    def _host_is_local(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip()

        return host in LOOPBACK

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)

        if not length:
            return {}

        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return {}

    # ---------- routing ----------

    def do_GET(self):
        if not self._host_is_local():
            return self._send(403, "forbidden", "text/plain; charset=utf-8")

        path = urllib.parse.urlparse(self.path).path

        if path == "/":
            return self._send(200, render.overview(self.hub))

        if path.startswith("/static/"):
            return self._static(path[len("/static/"):])

        if path == "/api/state":
            return self._json(200, self._state())

        if path.startswith("/api/"):
            panel_id = path[len("/api/"):]

            if panel_id not in sources.BY_ID:
                return self._json(404, {"error": "nieznany panel"})

            return self._json(200, store.read(panel_id) or store.blank(panel_id))

        if path.startswith("/p/"):
            rest = path[len("/p/"):].rstrip("/")
            fragment = rest.endswith("/fragment")
            panel_id = rest[:-len("/fragment")] if fragment else rest

            if panel_id not in sources.BY_ID:
                return self._send(404, "nie ma takiego panelu", "text/plain; charset=utf-8")

            if fragment:
                return self._send(200, render.fragment(panel_id))

            return self._send(200, render.panel_page(self.hub, panel_id))

        return self._send(404, "nie ma takiej strony", "text/plain; charset=utf-8")

    def do_POST(self):
        if not self._host_is_local():
            return self._json(403, {"error": "tylko localhost"})

        if self.headers.get("X-CSRF") != self.hub.csrf:
            return self._json(403, {"error": "brak lub zły token CSRF"})

        path = urllib.parse.urlparse(self.path).path
        body = self._body()

        if path == "/api/refresh":
            return self._refresh(body)

        if path == "/api/tempo/log":
            return self._tempo_write(body, write=True)

        if path == "/api/tempo/undo":
            return self._tempo_write(body, write=False)

        return self._json(404, {"error": "nieznana trasa"})

    # ---------- handlers ----------

    def _static(self, name):
        if "/" in name or ".." in name:
            return self._send(403, "nie", "text/plain; charset=utf-8")

        full = os.path.join(STATIC, name)

        if not os.path.isfile(full):
            return self._send(404, "brak pliku", "text/plain; charset=utf-8")

        with open(full, "rb") as handle:
            blob = handle.read()

        ext = os.path.splitext(name)[1]

        return self._send(200, blob, CONTENT_TYPES.get(ext, "application/octet-stream"))

    def _state(self):
        running = self.hub.runner.running()
        panels = []

        for panel in sources.PANELS:
            envelope = store.read(panel.id) or store.blank(panel.id)
            panels.append({
                "id": panel.id,
                "label": panel.label,
                "running": panel.id in running,
                "ok": envelope.get("error") is None and envelope.get("payload") is not None,
                "fetched_at": envelope.get("fetched_at"),
                "attempted_at": envelope.get("attempted_at"),
                "error": envelope.get("error"),
            })

        return {"panels": panels, "schedule": self.hub.scheduler.describe()}

    def _refresh(self, body):
        if body.get("all"):
            targets = [p.id for p in sources.PANELS]
        else:
            panel_id = body.get("panel")

            if panel_id not in sources.BY_ID:
                return self._json(400, {"error": "nieznany panel"})

            targets = [panel_id]

        threading.Thread(target=self._run_many, args=(targets,), daemon=True).start()

        return self._json(202, {"started": targets})

    def _run_many(self, targets):
        for panel_id in targets:
            self.hub.runner.run_panel(panel_id)

    def _tempo_write(self, body, write):
        """The only path that touches Jira. Never reachable without an explicit confirmation."""
        from . import tempo

        if body.get("confirm") is not True:
            return self._json(400, {"error": "zapis wymaga potwierdzenia"})

        day = (body.get("day") or "").strip()

        if not tempo.is_day(day):
            return self._json(400, {"error": "zły format dnia (YYYY-MM-DD)"})

        if write:
            result = tempo.log_day(day, (body.get("entries") or "").strip())
        else:
            result = tempo.undo_day(day)

        threading.Thread(target=self.hub.runner.run_panel, args=("tempo",), daemon=True).start()

        return self._json(200 if result["ok"] else 422, result)


class HubServerV6(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def _bind(address, port):
    """Both loopbacks: `localhost` resolves to ::1 first here, 127.0.0.1 is what curl picks."""
    server = HubServerV6 if ":" in address else ThreadingHTTPServer

    try:
        return server((address, port), Handler)
    except OSError:
        return None


def serve(port=None):
    os.makedirs(DATA_DIR, exist_ok=True)

    port = int(port or os.environ.get("WORK_HUB_PORT") or 8787)
    Handler.hub = Hub()
    Handler.hub.scheduler.start()

    servers = [s for s in (_bind("127.0.0.1", port), _bind("::1", port)) if s]

    if not servers:
        raise SystemExit("work-hub: port %d jest zajęty" % port)

    for extra in servers[1:]:
        threading.Thread(target=extra.serve_forever, daemon=True).start()

    print("work-hub: http://localhost:%d (%d %s)" % (
        port, len(servers), "gniazdo" if len(servers) == 1 else "gniazda"), flush=True)

    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.server_close()


if __name__ == "__main__":
    serve()
