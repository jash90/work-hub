"""A queued panel reads as busy until its own run ends, so "Refresh all" is followed to the end."""
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from . import context  # noqa: F401
from workhub import runner, server, sources

FIRST, SECOND = sources.PANELS[0].id, sources.PANELS[1].id


class Queue(unittest.TestCase):
    def setUp(self):
        self.runner = runner.Runner()

    def test_queued_panels_count_as_running(self):
        self.runner.queue([FIRST, SECOND])

        self.assertEqual({FIRST, SECOND}, self.runner.running())
        self.assertTrue(self.runner.is_running(SECOND))

    def test_a_finished_run_leaves_the_rest_of_the_queue_busy(self):
        self.runner.queue([FIRST, SECOND])

        with mock.patch.object(runner, "run_command", return_value={}):
            self.runner.run_panel(FIRST)

        self.assertEqual({SECOND}, self.runner.running())

    def test_a_panel_already_in_flight_leaves_the_queue(self):
        self.runner.queue([FIRST])
        self.runner._locks[FIRST].acquire()

        try:
            self.assertIsNone(self.runner.run_panel(FIRST))
        finally:
            self.runner._locks[FIRST].release()

        self.assertEqual(set(), self.runner.running())


class RefreshAll(unittest.TestCase):
    def setUp(self):
        self.release = threading.Event()
        hub = server.Hub()
        hub.runner.run_panel = lambda panel_id: self.release.wait(5)
        server.Handler.hub = hub
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.release.set()
        self.httpd.shutdown()
        self.httpd.server_close()

    def call(self, path, body=None):
        headers = {"X-CSRF": server.Handler.hub.csrf} if body is not None else {}
        request = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.httpd.server_address[1], path),
            data=json.dumps(body).encode() if body is not None else None, headers=headers)

        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    def test_every_panel_reads_as_running_right_after_the_click(self):
        started = self.call("/api/refresh", {"all": True})["started"]
        state = self.call("/api/state")

        self.assertEqual([p.id for p in sources.PANELS], started)
        self.assertTrue(all(panel["running"] for panel in state["panels"]))


if __name__ == "__main__":
    unittest.main()
