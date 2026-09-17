"""The HTTP guards, exercised against a real socket on an ephemeral port."""
import json
import os
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

    def test_tempo_replace_is_guarded_like_a_write_because_it_is_one(self):
        """It edits and deletes worklogs, so it must not be reachable more cheaply than log."""
        status, body = self.call("/api/tempo/replace", "POST",
                                 {"day": "2026-09-07", "entries": "ABC-1=8"},
                                 {"X-CSRF": self.csrf})

        self.assertEqual(400, status)
        self.assertIn("potwierdzenia", body)

        status, body = self.call("/api/tempo/replace", "POST",
                                 {"day": "wczoraj", "confirm": True}, {"X-CSRF": self.csrf})

        self.assertEqual(400, status)
        self.assertIn("format", body)

    def test_tempo_replace_needs_the_csrf_token(self):
        status, _ = self.call("/api/tempo/replace", "POST",
                              {"day": "2026-09-07", "confirm": True}, {})

        self.assertEqual(403, status)

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

    # ---------- settings ----------

    def test_the_settings_page_renders(self):
        status, body = self.call("/settings")

        self.assertEqual(200, status)
        self.assertIn("Ustawienia", body)

    def test_settings_are_refused_to_a_foreign_host(self):
        self.assertEqual(403, self.call("/settings", headers={"Host": "evil.example.com"})[0])

    def test_saving_settings_needs_the_csrf_token(self):
        status, _ = self.call("/api/settings", "POST", {"values": {"TEMPO_USER": "x"}})

        self.assertEqual(403, status)

    def test_an_unknown_setting_is_rejected(self):
        status, body = self.call("/api/settings", "POST", {"values": {"RM_RF": "nie"}},
                                 {"X-CSRF": self.csrf})

        self.assertEqual(400, status)
        self.assertIn("nieznane ustawienie", json.loads(body)["error"])

    def test_a_body_without_settings_is_rejected(self):
        status, _ = self.call("/api/settings", "POST", {"confirm": True}, {"X-CSRF": self.csrf})

        self.assertEqual(400, status)

    def test_a_saved_secret_is_reported_but_never_returned(self):
        status, _ = self.call("/api/settings", "POST",
                              {"values": {"JIRA_TOKEN": "tajne-haslo-9z1q"}},
                              {"X-CSRF": self.csrf})

        self.assertEqual(200, status)

        body = self.call("/api/settings")[1]
        item = next(i for i in json.loads(body)["settings"] if i["key"] == "JIRA_TOKEN")

        self.assertNotIn("tajne-haslo", body)
        self.assertTrue(item["set"])
        self.assertEqual("…9z1q", item["hint"])

    def test_a_saved_token_does_not_reach_the_secrets_directory_unasked(self):
        from workhub import config

        self.call("/api/settings", "POST", {"values": {"GITLAB_TOKEN": "bez-synchronizacji"}},
                  {"X-CSRF": self.csrf})

        self.assertFalse(os.path.exists(os.path.join(config.SECRETS_DIR,
                                                  config.SECRET_FILES["GITLAB_TOKEN"])))
