"""The HTTP guards, exercised against a real socket on an ephemeral port."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from . import context  # noqa: F401
from workhub import server


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.Handler.hub = server.Hub()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.csrf = server.Handler.hub.csrf

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def call(self, path, method="GET", body=None, headers=None):
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method,
                                         headers=headers or {})

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    # ---------- CSRF ----------

    def test_post_without_token_is_refused(self):
        status, _ = self.call("/api/refresh", "POST", {"panel": "testing"})

        self.assertEqual(403, status)

    def test_post_with_wrong_token_is_refused(self):
        status, _ = self.call("/api/refresh", "POST", {"panel": "testing"},
                              {"X-CSRF": "nie-ten"})

        self.assertEqual(403, status)

    # ---------- DNS rebinding ----------

    def test_foreign_host_header_is_refused(self):
        status, _ = self.call("/", headers={"Host": "evil.example.com"})

        self.assertEqual(403, status)

    def test_foreign_host_cannot_post_even_with_a_token(self):
        status, _ = self.call("/api/refresh", "POST", {"panel": "testing"},
                              {"Host": "evil.example.com", "X-CSRF": self.csrf})

        self.assertEqual(403, status)

    # ---------- the write path ----------

    def test_tempo_log_needs_an_explicit_confirmation(self):
        status, body = self.call("/api/tempo/log", "POST", {"day": "2026-09-07"},
                                 {"X-CSRF": self.csrf})

        self.assertEqual(400, status)
        self.assertIn("potwierdzenia", body)

    def test_tempo_log_validates_the_day(self):
        status, body = self.call("/api/tempo/log", "POST",
                                 {"day": "wczoraj", "confirm": True}, {"X-CSRF": self.csrf})

        self.assertEqual(400, status)
        self.assertIn("format", body)

    # ---------- static files ----------

    def test_static_path_cannot_escape(self):
        status, _ = self.call("/static/%2e%2e/server.py")

        self.assertEqual(403, status)

    def test_stylesheet_is_served(self):
        status, body = self.call("/static/app.css")

        self.assertEqual(200, status)
        self.assertIn("--accent", body)

    # ---------- ordinary reads ----------

    def test_overview_renders(self):
        status, body = self.call("/")

        self.assertEqual(200, status)
        self.assertIn("work-hub", body)

    def test_state_lists_every_panel(self):
        from workhub import sources

        status, body = self.call("/api/state")

        self.assertEqual(200, status)
        self.assertEqual(len(sources.PANELS), len(json.loads(body)["panels"]))

    def test_unknown_panel_is_a_404(self):
        self.assertEqual(404, self.call("/p/nie-ma")[0])
        self.assertEqual(404, self.call("/api/nie-ma")[0])

    def test_refresh_of_unknown_panel_is_rejected(self):
        status, _ = self.call("/api/refresh", "POST", {"panel": "nie-ma"},
                              {"X-CSRF": self.csrf})

        self.assertEqual(400, status)
