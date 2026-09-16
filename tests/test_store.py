import unittest

from . import context  # noqa: F401
from workhub import store


class Envelopes(unittest.TestCase):
    def setUp(self):
        self.panel = "test-panel"

    def test_failure_keeps_the_last_good_payload(self):
        """The invariant the whole hub leans on: stale data beats an empty page."""
        store.record_success(self.panel, {"main": {"n": 1}}, 10, now=1000)
        store.record_failure(self.panel, "HTTP 400", exit_code=1, now=2000)

        envelope = store.read(self.panel)

        self.assertEqual({"main": {"n": 1}}, envelope["payload"])
        self.assertEqual(1000, envelope["fetched_at"], "fetched_at must still date the payload")
        self.assertEqual(2000, envelope["attempted_at"])
        self.assertEqual("HTTP 400", envelope["error"])
        self.assertTrue(store.is_stale(envelope))

    def test_success_clears_an_earlier_error(self):
        store.record_failure(self.panel, "VPN", now=1000)
        store.record_success(self.panel, {"main": 2}, 5, now=3000)

        envelope = store.read(self.panel)

        self.assertIsNone(envelope["error"])
        self.assertFalse(store.is_stale(envelope))

    def test_unknown_panel_reads_as_nothing(self):
        self.assertIsNone(store.read("never-run"))
        self.assertIsNone(store.blank("never-run")["payload"])

    def test_failure_without_history_has_no_payload(self):
        store.record_failure("fresh-fail", "brak VPN", now=1000)
        envelope = store.read("fresh-fail")

        self.assertIsNone(envelope["payload"])
        self.assertFalse(store.is_stale(envelope), "nothing to show is not the same as stale")
