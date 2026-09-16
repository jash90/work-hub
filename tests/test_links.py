"""Joining a ticket to its merge request, from payloads the hub already has."""
import unittest

from . import context  # noqa: F401
from workhub import links

RELEASES = {"main": {"mrs": {
    "ABC-1": [{"key": "ABC-1", "iid": "706", "web_url": "https://gl/706",
                  "repo": "team-portal", "title": "fix(ABC-1): coś",
                  "approval_count": 2, "unresolved": 0}],
}}}

DASHBOARD = {"main": {
    "tasks": [{"key": "ABC-9", "mrs": [{"iid": "676", "web_url": "https://gl/676",
                                           "repo": "team-portal"}]}],
    "ready": [],
    "other_mrs": [{"key": "ABC-1", "iid": "706", "web_url": "https://gl/706",
                   "repo": "team-portal", "approval_count": 99}],
}}

QUEUE = {"main": {"queue": [{"jira_key": "DEF-5", "iid": 700, "web_url": "https://gl/700",
                             "project": "other/other-mobile", "open_threads": 3}]}}

REQUEST = {"main": {"merge_requests": [{"jira_key": "ABC-2", "iid": "721",
                                        "url": "https://gl/721", "project": "group/team-portal",
                                        "approvals": 0}]}}

PAYLOADS = {"releases": RELEASES, "dashboard": DASHBOARD,
            "review-queue": QUEUE, "pr-request": REQUEST}


def fake_read(panel_id):
    return PAYLOADS.get(panel_id)


class BuildingTheIndex(unittest.TestCase):
    def setUp(self):
        self.index = links.build(read=fake_read)

    def test_every_source_contributes(self):
        self.assertEqual({"ABC-1", "ABC-2", "ABC-9", "DEF-5"}, set(self.index))

    def test_an_mr_seen_twice_is_kept_once(self):
        """!706 appears in both the release board and the dashboard."""
        self.assertEqual(1, len(self.index["ABC-1"]))

    def test_the_richest_source_wins(self):
        """releases is read first, so its approval count is the one kept."""
        self.assertEqual(2, self.index["ABC-1"][0]["approvals"])

    def test_numeric_iids_become_strings(self):
        self.assertEqual("700", self.index["DEF-5"][0]["iid"])

    def test_threads_carry_over(self):
        self.assertEqual(3, self.index["DEF-5"][0]["unresolved"])

    def test_a_panel_that_never_ran_is_skipped(self):
        index = links.build(read=lambda panel_id: None)

        self.assertEqual({}, index)

    def test_a_broken_payload_does_not_break_the_join(self):
        index = links.build(read=lambda panel_id: RELEASES if panel_id == "releases" else "śmieci")

        self.assertIn("ABC-1", index)

    def test_an_mr_without_a_key_is_dropped(self):
        payload = {"main": {"merge_requests": [{"jira_key": None, "iid": "1", "url": "https://gl/1"}]}}
        index = links.build(read=lambda panel_id: payload if panel_id == "pr-request" else None)

        self.assertEqual({}, index)


class DriftRows(unittest.TestCase):
    """A ticket in testing has a merged MR, which only the drift rows still mention."""

    def index(self, url):
        payload = {"main": {"drift": [{"label": "ABC-7", "url": url, "detail": "MR wjechał"}]}}

        return links.build(read=lambda panel_id: payload if panel_id == "dashboard" else None)

    def test_a_merged_mr_is_picked_up_from_drift(self):
        index = self.index("https://gitlab.example.com/kan/team-portal/-/merge_requests/676")

        self.assertEqual("676", index["ABC-7"][0]["iid"])
        self.assertEqual("team-portal", index["ABC-7"][0]["repo"])

    def test_a_drift_row_pointing_elsewhere_is_ignored(self):
        self.assertEqual({}, self.index("https://jira.example.com/browse/ABC-7"))

    def test_a_drift_row_without_a_url_is_ignored(self):
        self.assertEqual({}, self.index(None))


class Merging(unittest.TestCase):
    def test_the_panel_keeps_its_own_mrs_first(self):
        own = [{"iid": "676", "web_url": "https://gl/676", "repo": "team-portal"}]
        extra = [{"key": "X", "iid": "999", "url": "https://gl/999", "repo": "team-portal"}]

        merged = links.merge(own, extra)

        self.assertEqual(["676", "999"], [m["iid"] for m in merged])
        self.assertEqual("https://gl/676", merged[0]["url"], "own MRs must gain a url too")

    def test_the_same_mr_is_not_listed_twice(self):
        own = [{"iid": "706", "web_url": "https://gl/706", "repo": "team-portal"}]
        extra = [{"key": "X", "iid": "706", "url": "https://gl/706", "repo": "team-portal"}]

        self.assertEqual(1, len(links.merge(own, extra)))

    def test_nothing_on_either_side_is_fine(self):
        self.assertEqual([], links.merge(None, None))
